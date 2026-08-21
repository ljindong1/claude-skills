"""AUTOSAR 산출물 추적 지도 생성기 v3 — 4단계 파이프라인.

프로젝트 폴더를 단계별로 분석하고, 각 단계마다 사람이 확인할 수 있는
HTML 화면과 다음 단계 입력이 되는 JSON을 출력한다.

  단계 1  폴더 구조 분석      -> stage1_structure.json + 1_structure.html
  단계 2  ARXML 분류·해석     -> stage2_arxml.json     + 2_arxml.html
  단계 3  모듈 구성·소스 매칭 -> stage3_modules.json   + 3_modules.html + report.txt
  단계 4  의존 그래프·지도    -> graph.json            + map.html

각 단계는 앞 단계의 JSON을 입력으로 읽는다. 단계 4는 파일 시스템을
다시 읽지 않으므로, 화면(map.html)만 고친 새 스크립트를 받았을 때는
`--stage 4` 재실행만으로 몇 초 만에 다시 그릴 수 있다 (재스캔 불필요).

추적 단위는 '파일'이다. 파라미터 단위는 다루지 않는다.
벤더 규칙은 아래 상수(LAYER_RULES / GENERATED_DIR_HINTS / SYSTEM_ARXML_RULES /
DEFINITION_TAGS / REF_NOISE)에 모여 있으므로, 다른 스택에 적용할 때는
이 부분만 수정하면 된다. 현재 값은 모빌진 클래식 기준으로 검증되었다.

표준 라이브러리만 사용한다. pip 설치 불필요, 인터넷 불필요, 읽기 전용.

Usage:
    python autosar_map.py "<과제 루트 경로>" --stage 0      # 사전 점검부터
    python autosar_map.py "<과제 루트 경로>" --stage all
    (출력은 기본적으로 과제 폴더 옆 <과제명>_map 에 생성된다. -o 로 바꿀 수 있다.)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SCRIPT_VERSION = "3.0"

ARXML_SUFFIXES: frozenset[str] = frozenset({".arxml"})
SOURCE_SUFFIXES: frozenset[str] = frozenset({".c", ".h"})

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {".git", ".svn", ".metadata", "__pycache__", "node_modules", ".settings"}
)

# --- 계층 분류 규칙 (경로 조각 소문자 매칭, 위에서부터 먼저 맞는 것 적용) ---
LAYER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DEVICE_HDR", ("b_mcal_base_nxp", "/header/")),
    ("LIB", ("cryptolib/",)),
    ("MCAL", ("mcal_output/", "/b_mcal_", "configuration/ecu/mcal/")),
    ("RTE_SWC", ("/rte/", "/swc/", "rte_output/")),
    ("BSW", ("bsw_output/", "static_code/", "configuration/ecu", "configuration/system")),
)
LAYER_ORDER: tuple[str, ...] = ("BSW", "MCAL", "RTE_SWC", "LIB", "DEVICE_HDR", "ETC")
LAYER_LABELS: dict[str, str] = {
    "BSW": "BSW",
    "MCAL": "MCAL",
    "RTE_SWC": "RTE/SWC",
    "LIB": "외부 라이브러리",
    "DEVICE_HDR": "MCU 디바이스 헤더",
    "ETC": "기타",
}
# 모듈로 취급하지 않는 계층 (파일 수만 집계)
NON_MODULE_LAYERS: frozenset[str] = frozenset({"DEVICE_HDR", "LIB"})

GENERATED_DIR_HINTS: tuple[str, ...] = ("generated/", "_output/", "/gen/", "autogen")
GENERATED_NAME_HINTS: tuple[str, ...] = ("_cfg", "_pbcfg", "_lcfg", "_pchcfg", "_cbk")

DEFINITION_DIR_HINTS: tuple[str, ...] = ("bswmd", "/def/", "definition")

# ARXML에서 정의를 담는 태그들 (BSWMD 템플릿 + ECUC 파라미터 정의 템플릿)
DEFINITION_TAGS: frozenset[str] = frozenset(
    {"ECUC-MODULE-DEF", "BSW-MODULE-DESCRIPTION"}
)
VALUE_TAG: str = "ECUC-MODULE-CONFIGURATION-VALUES"

# 참조 경로에서 모듈로 오인되기 쉬운 패키지/공용 이름
REF_NOISE: frozenset[str] = frozenset(
    {
        "AUTOSAR", "AUTRON", "ARRoot", "EcucDefs", "EcuC", "ActiveEcuC",
        "CommonPublishedInformation", "MemMap", "Compiler", "Platform",
    }
)

INCLUDE_PATTERN: re.Pattern[str] = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.M)
BSWMD_NAME_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:bswmd|ecucd|ecuc)[_\-]?(.+)$", re.IGNORECASE
)
SWCD_NAME_PATTERN: re.Pattern[str] = re.compile(r"^swcd(?:_bsw)?[_\-](.+)$", re.IGNORECASE)

# 모듈이 아니라 ECU 전체를 기술하는 ARXML (실패가 아니라 별도 종류)
SYSTEM_ARXML_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("통신 DB (CAN 매트릭스)", ("/dbimport/",)),
    ("값 컬렉션", ("ecucvaluecollection",)),
    ("시스템/컴포지션", ("/composition/", "ecuextract", "rootcomposition")),
    ("데이터 타입", ("/datatypes/",)),
    ("변환기(Transformer)", ("/transformer/",)),
    ("포트 인터페이스", ("portinterfaces",)),
)

NAME_NOISE_PREFIXES: tuple[str, ...] = ("BswModuleDescription", "BswImplementation")

STAGE_FILES: dict[int, str] = {
    0: "stage0_env.json",
    1: "stage1_structure.json",
    2: "stage2_arxml.json",
    3: "stage3_modules.json",
    4: "graph.json",
}

# ---------------------------------------------------------------- 공용 헬퍼

def to_slash(rel_path: str) -> str:
    """경로 구분자를 슬래시로 통일한다 (JSON/JS 일관성)."""
    return rel_path.replace("\\", "/")


def normalize(rel_path: str) -> str:
    """경로를 소문자 슬래시 형태로 정규화한다."""
    return "/" + to_slash(rel_path).lower()


def classify_layer(rel_path: str) -> str:
    """파일 경로로 계층을 판정한다."""
    lowered = normalize(rel_path)
    for layer, hints in LAYER_RULES:
        if any(hint in lowered for hint in hints):
            return layer
    return "ETC"


def strip_namespace(tag: str) -> str:
    """XML 태그에서 네임스페이스를 제거한다."""
    return tag.rsplit("}", 1)[-1]


def find_child_text(element: ET.Element, local_name: str) -> str | None:
    """직계 자식 중 지정한 로컬 태그명의 텍스트를 반환한다."""
    for child in element:
        if strip_namespace(child.tag) == local_name and child.text:
            return child.text.strip()
    return None


def extract_module_from_ref(ref_path: str) -> str | None:
    """AUTOSAR 참조 경로에서 모듈 후보를 뽑는다.

    `/AUTOSAR/EcucDefs/Adc/AdcConfigSet/AdcChannel` -> `Adc`
    (EcucDefs 바로 다음 세그먼트만 취한다. 없으면 포기한다.)
    """
    parts = [part for part in ref_path.split("/") if part]
    for index, part in enumerate(parts):
        if part.lower() in {"ecucdefs", "ecucmoduleconfigurationvalues"}:
            if index + 1 < len(parts):
                candidate = parts[index + 1]
                return None if candidate in REF_NOISE else candidate
    return None


def module_from_filename(stem: str) -> str | None:
    """`Bswmd_CanIf` 같은 파일명에서 모듈명을 뽑는다."""
    match = BSWMD_NAME_PATTERN.match(stem)
    if match:
        candidate = match.group(1).strip("_")
        return candidate or None
    return None


def module_from_swcd(stem: str) -> str | None:
    """`Swcd_Bsw_Dcm` 같은 파일명에서 모듈명을 뽑는다."""
    match = SWCD_NAME_PATTERN.match(stem)
    if match:
        candidate = match.group(1).strip("_")
        return candidate or None
    return None


def classify_system_arxml(rel_path: str) -> str | None:
    """모듈이 아닌 ECU 전체 기술 ARXML인지 판정한다."""
    lowered = normalize(rel_path)
    for kind, hints in SYSTEM_ARXML_RULES:
        if any(hint in lowered for hint in hints):
            return kind
    return None


def is_noise_name(name: str) -> bool:
    """모듈명으로 쓰면 안 되는 이름인지 판별한다."""
    if len(name) < 2 or not name[0].isupper():
        return True
    return name in REF_NOISE or name.startswith(NAME_NOISE_PREFIXES)


def is_definition_area(rel_path: str) -> bool:
    """정의 파일이 놓이는 폴더인지 판별한다."""
    lowered = normalize(rel_path)
    return any(hint in lowered for hint in DEFINITION_DIR_HINTS)


def is_generated(rel_path: str, stem: str) -> bool:
    """생성 파일 여부를 판별한다."""
    lowered = normalize(rel_path)
    if any(hint in lowered for hint in GENERATED_DIR_HINTS):
        return True
    return any(hint in stem.lower() for hint in GENERATED_NAME_HINTS)


def parse_includes(path: Path) -> list[str]:
    """소스 파일의 #include 대상 목록을 반환한다."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return sorted(set(INCLUDE_PATTERN.findall(text)))


def match_module(stem: str, sorted_modules: list[str]) -> str | None:
    """파일 stem에 맞는 모듈명을 찾는다 (긴 이름 우선)."""
    for name in sorted_modules:
        if stem == name or stem.startswith(f"{name}_"):
            return name
    return None


def guess_modules_from_sources(stems: list[str], known: set[str]) -> set[str]:
    """ARXML에 없던 모듈을 소스 파일명 접두사에서 추정한다."""
    counter: Counter[str] = Counter()
    for stem in stems:
        prefix = stem.split("_", 1)[0]
        if prefix and prefix not in known and prefix[0].isupper():
            counter[prefix] += 1
    return {prefix for prefix, count in counter.items() if count >= 2}


@dataclass(frozen=True, slots=True)
class ArxmlInfo:
    """ARXML 파일 하나에서 추출한 정보."""

    rel_path: str
    value_modules: tuple[str, ...]
    definition_modules: tuple[str, ...]
    referenced: tuple[str, ...]


def parse_arxml(path: Path, rel_path: str) -> ArxmlInfo | None:
    """ARXML에서 모듈 정의/값/참조를 추출한다.

    ECUC 태그가 없으면 BSWMD 템플릿 태그를 보고, 그것도 없으면
    파일명(Bswmd_XXX.arxml)으로 정의 파일 여부를 판단한다.
    """
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        logger.debug("ARXML 파싱 실패: %s (%s)", rel_path, exc)
        return None

    value_modules: list[str] = []
    definition_modules: list[str] = []
    referenced: set[str] = set()

    for element in tree.iter():
        local = strip_namespace(element.tag)
        if local == VALUE_TAG:
            short_name = find_child_text(element, "SHORT-NAME")
            if short_name:
                value_modules.append(short_name)
        elif local in DEFINITION_TAGS:
            short_name = find_child_text(element, "SHORT-NAME")
            if short_name and not is_noise_name(short_name):
                definition_modules.append(short_name)
        elif local in {"VALUE-REF", "DEFINITION-REF"} and element.text:
            module = extract_module_from_ref(element.text.strip())
            if module:
                referenced.add(module)

    if not (value_modules or definition_modules):
        guessed = module_from_filename(path.stem)
        if guessed and not is_noise_name(guessed) and is_definition_area(rel_path):
            definition_modules.append(guessed)

    if not (value_modules or definition_modules):
        return None

    return ArxmlInfo(
        rel_path=rel_path,
        value_modules=tuple(dict.fromkeys(value_modules)),
        definition_modules=tuple(dict.fromkeys(definition_modules)),
        referenced=tuple(sorted(referenced)),
    )


# ---------------------------------------------------------------- 입출력 헬퍼

def write_json(path: Path, data: dict) -> None:
    """JSON 파일을 쓴다."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_html(path: Path, template: str, data: dict) -> None:
    """템플릿에 데이터를 심어 단일 HTML 파일을 쓴다."""
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__DATA__", blob)
    html = html.replace("__LAYERS__", json.dumps(LAYER_LABELS, ensure_ascii=False))
    html = html.replace("__CSS__", BASE_CSS)
    path.write_text(html, encoding="utf-8")


def load_stage(out_dir: Path, stage: int) -> dict:
    """앞 단계 JSON을 읽는다. 없으면 안내 후 종료한다."""
    path = out_dir / STAGE_FILES[stage]
    if not path.exists():
        sys.exit(
            f"오류: {path} 가 없습니다.\n"
            f"먼저 `--stage {stage}` (또는 `--stage all`)를 실행하세요."
        )
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 단계 0

def run_stage0(root: Path, out_dir: Path) -> dict:
    """사전 점검 — 스캔 없이 입력·환경만 확인한다.

    최상위 폴더 구성을 미리 보여주어, 사용자가 '분석하려는 과제가 맞는지'
    스캔 전에 확인할 수 있게 한다 (0단계 게이트).
    """
    python_ok = sys.version_info >= (3, 10)
    root_ok = root.is_dir()

    top_dirs: list[str] = []
    top_files = 0
    approx_files = 0
    capped = False
    if root_ok:
        for child in sorted(root.iterdir()):
            if child.name in SKIP_DIR_NAMES:
                continue
            if child.is_dir():
                top_dirs.append(child.name)
            else:
                top_files += 1
        for count, _ in enumerate(root.rglob("*"), start=1):
            approx_files = count
            if count >= 300_000:
                capped = True
                break

    write_ok = True
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        probe = out_dir / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError:
        write_ok = False

    out_inside_root = root_ok and out_dir.is_relative_to(root)

    data = {
        "stage": 0,
        "version": SCRIPT_VERSION,
        "root": str(root),
        "output": str(out_dir),
        "python": ".".join(map(str, sys.version_info[:3])),
        "python_ok": python_ok,
        "root_ok": root_ok,
        "write_ok": write_ok,
        "out_inside_root": out_inside_root,
        "top_dirs": top_dirs,
        "top_files": top_files,
        "approx_files": approx_files,
        "approx_capped": capped,
    }
    if write_ok:
        write_json(out_dir / STAGE_FILES[0], data)
    print(stage0_summary(data))
    return data


def stage0_summary(data: dict) -> str:
    """단계 0 텍스트 요약 (stdout 붙여넣기용)."""
    ok = lambda flag: "OK" if flag else "문제 있음"  # noqa: E731
    lines = [
        "=== 단계 0: 사전 점검 ===",
        f"Python    : {data['python']}  "
        f"({'OK' if data['python_ok'] else '3.10 이상 필요 - 업그레이드 후 진행'})",
        f"과제 루트 : {data['root']}  ({ok(data['root_ok'])})",
        f"출력 폴더 : {data['output']}  (쓰기 {ok(data['write_ok'])})",
    ]
    if data["out_inside_root"]:
        lines.append("  ※ 출력 폴더가 과제 폴더 내부입니다 - 스캔에서 자동 제외되지만,"
                     " 외부 경로를 권장합니다")
    if data["root_ok"]:
        lines += [
            "",
            "[ 최상위 구성 ]",
            "  폴더: " + (", ".join(data["top_dirs"]) or "(없음)"),
            f"  루트 직속 파일: {data['top_files']}개",
            f"  전체 항목 수(대략): {data['approx_files']:,}"
            + (" 이상 (30만 개에서 집계 중단)" if data["approx_capped"] else ""),
        ]
    problems = not (data["python_ok"] and data["root_ok"] and data["write_ok"])
    lines += [
        "",
        ("-> 문제를 해결한 뒤 다시 --stage 0 을 실행하세요." if problems else
         "-> 위 최상위 구성이 분석하려는 과제가 맞는지 확인해 주세요."
         " 맞으면 --stage 1 로 진행합니다."),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- 단계 1

def run_stage1(root: Path, out_dir: Path) -> dict:
    """폴더 구조 분석 — 파일 인벤토리와 계층 판정. ARXML은 아직 열지 않는다."""
    files: list[dict] = []
    ext_counter: Counter[str] = Counter()
    dir_other: Counter[str] = Counter()
    layer_counter: Counter[str] = Counter()
    skip_out = out_dir if out_dir.is_relative_to(root) else None

    for path in root.rglob("*"):
        if not path.is_file() or SKIP_DIR_NAMES & set(path.parts):
            continue
        if skip_out is not None and path.is_relative_to(skip_out):
            continue  # 출력 폴더가 과제 내부여도 스캔에 섞이지 않게 한다
        suffix = path.suffix.lower()
        ext_counter[suffix or "(없음)"] += 1
        rel = to_slash(str(path.relative_to(root)))
        if suffix in ARXML_SUFFIXES or suffix in SOURCE_SUFFIXES:
            layer = classify_layer(rel)
            layer_counter[layer] += 1
            files.append({"path": rel, "ext": suffix, "layer": layer})
        else:
            parent = to_slash(str(path.parent.relative_to(root)))
            dir_other[parent] += 1

    data = {
        "stage": 1,
        "version": SCRIPT_VERSION,
        "root": str(root),
        "files": files,
        "dir_other_counts": dict(dir_other.most_common()),
        "extension_counts": dict(ext_counter.most_common()),
        "layer_file_counts": {
            layer: layer_counter.get(layer, 0)
            for layer in LAYER_ORDER
            if layer_counter.get(layer, 0)
        },
    }
    write_json(out_dir / STAGE_FILES[1], data)
    write_html(out_dir / "1_structure.html", TEMPLATE_STRUCTURE, data)
    print(stage1_summary(data))
    return data


def stage1_summary(data: dict) -> str:
    """단계 1 텍스트 요약 (stdout 붙여넣기용)."""
    files = data["files"]
    lines = [
        "=== 단계 1: 폴더 구조 분석 ===",
        f"스캔 루트 : {data['root']}",
        f"추적 대상 : ARXML {sum(1 for f in files if f['ext'] == '.arxml')}개, "
        f"소스(.c/.h) {sum(1 for f in files if f['ext'] != '.arxml')}개",
        "",
        "[ 계층 판정 결과 ]",
    ]
    for layer, count in data["layer_file_counts"].items():
        lines.append(f"  {LAYER_LABELS.get(layer, layer):<22}{count:>7}")

    etc = [f["path"] for f in files if f["layer"] == "ETC"]
    total = len(files)
    if etc:
        ratio = len(etc) / total * 100 if total else 0
        lines += ["", f"[ 계층 미판정(ETC) : {len(etc)}개 ({ratio:.1f}%) ]"]
        if ratio > 3:
            lines.append("  ※ 3% 초과 — LAYER_RULES가 이 과제 폴더 구조와 안 맞을 수 있음")
        for rel in etc[:15]:
            lines.append(f"  - {rel}")
        if len(etc) > 15:
            lines.append(f"  ... 외 {len(etc) - 15}개")

    lines += ["", "[ 확장자 분포 (상위 12) ]"]
    for ext, count in list(data["extension_counts"].items())[:12]:
        lines.append(f"  {ext:<14}{count:>7}")
    lines += ["", "-> 1_structure.html 을 브라우저로 열어 폴더 트리·계층 색을 확인하세요."]
    return "\n".join(lines)


# ---------------------------------------------------------------- 단계 2

def run_stage2(root: Path, out_dir: Path) -> dict:
    """ARXML 분류·해석 — 단계 1 인벤토리의 ARXML만 파싱한다."""
    stage1 = load_stage(out_dir, 1)
    records: list[dict] = []

    for entry in stage1["files"]:
        if entry["ext"] not in ARXML_SUFFIXES:
            continue
        rel = entry["path"]
        path = root / rel
        record: dict = {"path": rel, "layer": entry["layer"]}

        system_kind = classify_system_arxml(rel)
        if system_kind:
            record.update(kind="system", system_kind=system_kind)
            records.append(record)
            continue

        swcd_module = module_from_swcd(path.stem)
        if swcd_module:
            record.update(kind="swcd", module=swcd_module)
            records.append(record)
            continue

        info = parse_arxml(path, rel)
        if info is None:
            record.update(kind="unparsed")
            records.append(record)
            continue

        record.update(
            kind="value" if info.value_modules else "definition",
            value_modules=list(info.value_modules),
            definition_modules=list(info.definition_modules),
            referenced=list(info.referenced),
        )
        records.append(record)

    data = {
        "stage": 2,
        "version": SCRIPT_VERSION,
        "root": str(root),
        "arxml": records,
        "kind_counts": dict(Counter(r["kind"] for r in records).most_common()),
    }
    write_json(out_dir / STAGE_FILES[2], data)
    write_html(out_dir / "2_arxml.html", TEMPLATE_ARXML, data)
    print(stage2_summary(data))
    return data


KIND_LABELS: dict[str, str] = {
    "definition": "정의 (BSWMD)",
    "value": "값 (ECUC)",
    "swcd": "서비스 컴포넌트 (SWCD)",
    "system": "시스템 레벨",
    "unparsed": "해석 실패",
}


def stage2_summary(data: dict) -> str:
    """단계 2 텍스트 요약."""
    records = data["arxml"]
    total = len(records)
    lines = ["=== 단계 2: ARXML 분류·해석 ===", f"ARXML {total}개"]
    lines.append("")
    lines.append("[ 종류별 분포 ]")
    for kind, count in data["kind_counts"].items():
        lines.append(f"  {KIND_LABELS.get(kind, kind):<24}{count:>5}")

    system = [r for r in records if r["kind"] == "system"]
    if system:
        by_kind: dict[str, list[str]] = defaultdict(list)
        for r in system:
            by_kind[r["system_kind"]].append(r["path"])
        lines += ["", "[ 시스템 레벨 ARXML (모듈 소속 아님) ]"]
        for kind, paths in by_kind.items():
            lines.append(f"  {kind} ({len(paths)})")

    unparsed = [r["path"] for r in records if r["kind"] == "unparsed"]
    if unparsed:
        ratio = len(unparsed) / total * 100 if total else 0
        lines += ["", f"[ 해석 실패 : {len(unparsed)}개 ({ratio:.1f}%) ]"]
        if ratio > 5:
            lines.append("  ※ 5% 초과 — 새로운 ARXML 종류가 있을 가능성. 목록의 정체를 먼저 파악할 것")
        for rel in unparsed[:20]:
            lines.append(f"  - {rel}")
        if len(unparsed) > 20:
            lines.append(f"  ... 외 {len(unparsed) - 20}개")

    lines += ["", "-> 2_arxml.html 을 브라우저로 열어 파일→모듈 매핑을 확인하세요."]
    return "\n".join(lines)


# ---------------------------------------------------------------- 단계 3

def new_module(name: str) -> dict:
    """빈 모듈 노드를 만든다."""
    return {
        "name": name,
        "layer": "ETC",
        "definition_arxml": [],
        "value_arxml": [],
        "swcd_arxml": [],
        "generated_files": [],
        "static_files": [],
        "depends_on": [],
        "used_by": [],
        "is_unused": False,
    }


def run_stage3(root: Path, out_dir: Path) -> dict:
    """모듈 구성·소스 매칭 — 모듈 노드를 만들고 소스를 배정한다."""
    stage1 = load_stage(out_dir, 1)
    stage2 = load_stage(out_dir, 2)

    modules: dict[str, dict] = {}
    files_map: dict[str, dict] = {}
    pending_refs: dict[str, set[str]] = defaultdict(set)
    layer_votes: dict[str, Counter[str]] = defaultdict(Counter)
    system_arxml: dict[str, list[str]] = defaultdict(list)
    unparsed: list[str] = []

    def node(name: str) -> dict:
        return modules.setdefault(name, new_module(name))

    # 1) 단계 2 결과를 모듈로 조립
    for record in stage2["arxml"]:
        rel = record["path"]
        files_map[rel] = {"type": "arxml", **record}
        kind = record["kind"]
        if kind == "system":
            system_arxml[record["system_kind"]].append(rel)
            continue
        if kind == "unparsed":
            unparsed.append(rel)
            continue
        if kind == "swcd":
            module_name = record["module"]
            node(module_name)["swcd_arxml"].append(rel)
            layer_votes[module_name][record["layer"]] += 1
            continue
        for module_name in record.get("definition_modules", []):
            node(module_name)["definition_arxml"].append(rel)
        for module_name in record.get("value_modules", []):
            node(module_name)["value_arxml"].append(rel)
            pending_refs[module_name].update(record.get("referenced", []))
            # 값 ARXML은 계층 판정의 최우선 근거.
            # Configuration\ECU 직속(BSW)이 Mcal 하위보다 강하다 (Dem/EcuM 대응).
            layer_votes[module_name][record["layer"]] += (
                100 if record["layer"] == "BSW" else 60
            )

    # 2) 소스 파일명에서 모듈 보충 (디바이스 헤더/외부 라이브러리는 제외)
    source_entries = [
        entry
        for entry in stage1["files"]
        if entry["ext"] in SOURCE_SUFFIXES and entry["layer"] not in NON_MODULE_LAYERS
    ]
    guessed = guess_modules_from_sources(
        [Path(entry["path"]).stem for entry in source_entries], set(modules)
    )
    for name in guessed:
        node(name)

    sorted_modules = sorted(modules, key=len, reverse=True)

    # 3) 소스 배정 + #include 의존 수집
    unmatched: list[str] = []
    for entry in source_entries:
        rel = entry["path"]
        stem = Path(rel).stem
        includes = parse_includes(root / rel)
        generated = is_generated(rel, stem)
        module_name = match_module(stem, sorted_modules)
        files_map[rel] = {
            "type": "source",
            "path": rel,
            "module": module_name,
            "generated": generated,
            "layer": entry["layer"],
            "includes": includes,
        }
        if module_name is None:
            unmatched.append(rel)
            continue

        target_node = modules[module_name]
        if entry["layer"] != "ETC":
            layer_votes[module_name][entry["layer"]] += 1
        (target_node["generated_files"] if generated
         else target_node["static_files"]).append(rel)

        for included in includes:
            target = match_module(Path(included).stem, sorted_modules)
            if target and target != module_name:
                pending_refs[module_name].add(target)

    # 4) 의존 관계를 '실존 모듈'로만 확정 (핵심 보정)
    for module_name, refs in pending_refs.items():
        target_node = modules.get(module_name)
        if target_node is None:
            continue
        target_node["depends_on"] = sorted(
            ref for ref in refs
            if ref in modules and ref != module_name and ref not in REF_NOISE
        )

    # 5) 역방향 의존 + 계층 확정 + 미사용 판정
    for target_node in modules.values():
        for target in target_node["depends_on"]:
            other = modules[target]
            if target_node["name"] not in other["used_by"]:
                other["used_by"].append(target_node["name"])

    for target_node in modules.values():
        target_node["used_by"].sort()
        for key in ("definition_arxml", "value_arxml", "swcd_arxml"):
            target_node[key] = sorted(set(target_node[key]))
        target_node["generated_files"].sort()
        target_node["static_files"].sort()

        votes = layer_votes.get(target_node["name"])
        if votes:
            target_node["layer"] = votes.most_common(1)[0][0]

        target_node["is_unused"] = (
            bool(target_node["definition_arxml"])
            and not target_node["value_arxml"]
            and not target_node["generated_files"]
            and not target_node["static_files"]
            and not target_node["swcd_arxml"]
        )

    merge_swcd_only_modules(modules, files_map)

    data = {
        "stage": 3,
        "version": SCRIPT_VERSION,
        "root": str(root),
        "modules": modules,
        "files": files_map,
        "system_arxml": {kind: sorted(paths) for kind, paths in system_arxml.items()},
        "unmatched_sources": unmatched,
        "unparsed_arxml": unparsed,
        "layer_file_counts": stage1["layer_file_counts"],
        "extension_counts": stage1["extension_counts"],
    }
    write_json(out_dir / STAGE_FILES[3], data)
    write_html(out_dir / "3_modules.html", TEMPLATE_MODULES, data)
    (out_dir / "report.txt").write_text(build_text_report(data), encoding="utf-8")
    print(stage3_summary(data))
    return data


def merge_swcd_only_modules(modules: dict[str, dict], files_map: dict[str, dict]) -> None:
    """SWCD만 있는 파생 모듈을 상위 모듈로 흡수한다.

    `Swcd_Bsw_WdgM_Fixed.arxml` 이 만든 `WdgM_Fixed` 를 `WdgM` 으로 합친다.
    """
    for name in list(modules):
        target_node = modules[name]
        has_only_swcd = (
            target_node["swcd_arxml"]
            and not target_node["definition_arxml"]
            and not target_node["value_arxml"]
            and not target_node["generated_files"]
            and not target_node["static_files"]
        )
        if not has_only_swcd or "_" not in name:
            continue
        parent = name.rsplit("_", 1)[0]
        while parent and parent not in modules:
            parent = parent.rsplit("_", 1)[0] if "_" in parent else ""
        if parent:
            parent_node = modules[parent]
            parent_node["swcd_arxml"] = sorted(
                set(parent_node["swcd_arxml"]) | set(target_node["swcd_arxml"])
            )
            parent_node["is_unused"] = False
            for rel in target_node["swcd_arxml"]:
                if rel in files_map:
                    files_map[rel]["module"] = parent
            del modules[name]


def stage3_summary(data: dict) -> str:
    """단계 3 텍스트 요약."""
    modules = data["modules"]
    unused = [name for name, m in modules.items() if m["is_unused"]]
    lines = [
        "=== 단계 3: 모듈 구성·소스 매칭 ===",
        f"모듈 수 : {len(modules)}  (미사용 {len(unused)}개 포함)",
        "",
    ]
    for layer in LAYER_ORDER:
        names = sorted(
            n for n, m in modules.items() if m["layer"] == layer and not m["is_unused"]
        )
        if names:
            lines.append(f"  {LAYER_LABELS[layer]:<22}{len(names):>4}개")
    if unused:
        lines += ["", f"[ 미사용 모듈 : {len(unused)}개 ]", "  " + ", ".join(sorted(unused))]

    suspicious = sorted(
        n for n in modules
        if len(n) < 2 or not n[0].isupper()
    )
    if suspicious:
        lines += ["", f"[ 의심 모듈명 (1글자/소문자 시작) : {len(suspicious)}개 ]",
                  "  " + ", ".join(suspicious)]

    unmatched = data["unmatched_sources"]
    if unmatched:
        total_sources = sum(
            1 for f in data["files"].values() if f["type"] == "source"
        )
        ratio = len(unmatched) / total_sources * 100 if total_sources else 0
        lines += ["", f"[ 모듈 매칭 실패 소스 : {len(unmatched)}개 ({ratio:.1f}%) ]"]
        if ratio > 1:
            lines.append("  ※ 1% 초과 — 벤더 고유 명명 규칙이 있을 수 있음")
        for rel in unmatched[:25]:
            lines.append(f"  - {rel}")
        if len(unmatched) > 25:
            lines.append(f"  ... 외 {len(unmatched) - 25}개")

    lines += ["", "-> 3_modules.html 을 브라우저로 열어 모듈 구성·산출물 분포를 확인하세요.",
              "   (전체 표는 report.txt 에도 있습니다)"]
    return "\n".join(lines)


def build_text_report(data: dict) -> str:
    """사람이 읽는 구조 리포트 문자열을 만든다 (구 report.txt 호환)."""
    modules = data["modules"]
    lines: list[str] = []
    add = lines.append
    unused = [name for name, m in modules.items() if m["is_unused"]]

    add(f"스캔 루트 : {data['root']}")
    add(f"모듈 수   : {len(modules)}  (미사용 {len(unused)}개 포함)")
    add("")

    add("[ 계층별 파일 수 ]")
    for layer, count in data["layer_file_counts"].items():
        add(f"  {LAYER_LABELS.get(layer, layer):<22}{count:>7}")
    add("")

    add("[ 확장자 분포 ]")
    for extension, count in list(data["extension_counts"].items())[:12]:
        add(f"  {extension:<14}{count:>7}")
    add("")

    for layer in LAYER_ORDER:
        names = sorted(
            name for name, m in modules.items()
            if m["layer"] == layer and not m["is_unused"]
        )
        if not names:
            continue
        add(f"[ {LAYER_LABELS[layer]} 모듈 : {len(names)}개 ]")
        add(f"  {'모듈':<20}{'정의':>5}{'값':>4}{'SWCD':>6}{'생성':>6}{'정적':>6}  의존")
        add("  " + "-" * 66)
        for name in names:
            m = modules[name]
            depends = ", ".join(m["depends_on"][:7])
            if len(m["depends_on"]) > 7:
                depends += f" 외 {len(m['depends_on']) - 7}"
            add(
                f"  {name:<20}{len(m['definition_arxml']):>5}{len(m['value_arxml']):>4}"
                f"{len(m['swcd_arxml']):>6}{len(m['generated_files']):>6}"
                f"{len(m['static_files']):>6}  {depends}"
            )
        add("")

    if data["system_arxml"]:
        total = sum(len(paths) for paths in data["system_arxml"].values())
        add(f"[ 시스템 레벨 ARXML (모듈 소속 아님) : {total}개 ]")
        for kind, paths in data["system_arxml"].items():
            add(f"  {kind} ({len(paths)})")
            for rel_path in paths[:4]:
                add(f"    - {rel_path}")
            if len(paths) > 4:
                add(f"    ... 외 {len(paths) - 4}개")
        add("")

    if unused:
        add(f"[ 미사용 모듈 (정의만 있고 값·생성코드 없음) : {len(unused)}개 ]")
        add("  " + ", ".join(sorted(unused)))
        add("")

    if data["unparsed_arxml"]:
        add(f"[ 해석 실패 ARXML : {len(data['unparsed_arxml'])}개 ]")
        for rel_path in data["unparsed_arxml"][:20]:
            add(f"  - {rel_path}")
        add("")

    if data["unmatched_sources"]:
        add(f"[ 모듈 매칭 실패 소스 : {len(data['unmatched_sources'])}개 ]")
        for rel_path in data["unmatched_sources"][:25]:
            add(f"  - {rel_path}")
        add("")

    return "\n".join(lines)


# ---------------------------------------------------------------- 단계 4

def compute_levels(modules: dict[str, dict]) -> dict[str, int]:
    """의존 방향으로 모듈 배치 레벨을 계산한다 (MCAL이 0, 위로 갈수록 커짐).

    순환 의존(EcuM↔BswM, Can↔CanIf 등)이 흔하므로, 먼저 Tarjan SCC로
    순환 묶음을 찾아 한 덩어리로 취급한 뒤 축약 그래프(DAG)에서
    최장 경로로 레벨을 매긴다. 같은 순환에 속한 모듈은 같은 레벨이 된다.
    배치가 어색하면 여기와 map.html 렌더링을 함께 손본다.
    """
    graph = {
        name: [d for d in module["depends_on"] if d in modules]
        for name, module in modules.items()
    }

    # --- Tarjan SCC (반복 구현, 재귀 한도 회피) ---
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []
    counter = 0

    for root_name in graph:
        if root_name in index:
            continue
        index[root_name] = low[root_name] = counter
        counter += 1
        stack.append(root_name)
        on_stack.add(root_name)
        work: list[tuple[str, "object"]] = [(root_name, iter(graph[root_name]))]
        while work:
            node_name, neighbors = work[-1]
            advanced = False
            for neighbor in neighbors:
                if neighbor not in index:
                    index[neighbor] = low[neighbor] = counter
                    counter += 1
                    stack.append(neighbor)
                    on_stack.add(neighbor)
                    work.append((neighbor, iter(graph[neighbor])))
                    advanced = True
                    break
                if neighbor in on_stack:
                    low[node_name] = min(low[node_name], index[neighbor])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node_name])
            if low[node_name] == index[node_name]:
                component: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.append(member)
                    if member == node_name:
                        break
                sccs.append(component)

    # --- 축약 그래프에서 레벨 계산 (Tarjan 방출 순서 = 의존이 먼저) ---
    comp_id = {name: i for i, comp in enumerate(sccs) for name in comp}
    comp_level: dict[int, int] = {}
    for i, comp in enumerate(sccs):
        all_low = all(
            modules[name]["layer"] in {"MCAL", "DEVICE_HDR"} for name in comp
        )
        level = 0 if all_low else 1
        for name in comp:
            for dep in graph[name]:
                if comp_id[dep] != i:
                    level = max(level, comp_level[comp_id[dep]] + 1)
        comp_level[i] = min(level, 12)

    levels: dict[str, int] = {}
    for name in graph:
        # MCAL은 시각적으로 최하단 열에 고정한다
        levels[name] = 0 if modules[name]["layer"] == "MCAL" else comp_level[comp_id[name]]
    return levels


def run_stage4(out_dir: Path) -> dict:
    """의존 그래프·지도 — 파일 시스템을 읽지 않고 단계 3 JSON만으로 렌더링한다."""
    stage3 = load_stage(out_dir, 3)
    levels = compute_levels(stage3["modules"])
    for name, level in levels.items():
        stage3["modules"][name]["level"] = level

    data = {**stage3, "stage": 4, "version": SCRIPT_VERSION}
    write_json(out_dir / STAGE_FILES[4], data)
    write_html(out_dir / "map.html", TEMPLATE_MAP, data)
    print(stage4_summary(data))
    return data


def stage4_summary(data: dict) -> str:
    """단계 4 텍스트 요약."""
    modules = data["modules"]
    edge_count = sum(len(m["depends_on"]) for m in modules.values())
    level_dist = Counter(m.get("level", 0) for m in modules.values() if not m["is_unused"])
    lines = [
        "=== 단계 4: 의존 그래프·지도 ===",
        f"노드(모듈) {len(modules)}개, 링크(의존) {edge_count}개",
        "레벨 분포 : " + ", ".join(
            f"L{lv}:{count}" for lv, count in sorted(level_dist.items())
        ),
        "",
        "-> map.html 을 브라우저로 열어보세요.",
        "   전체 지도가 한 화면에 뜨고, 모듈을 클릭하면 그 자리에서 하이라이트됩니다.",
        "   우측 패널의 파일 사각형을 클릭하면 ARXML/소스 상세 정보가 표시됩니다.",
        "   화면만 고칠 때는 새 스크립트로 `--stage 4`만 재실행하면 됩니다 (재스캔 불필요).",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="AUTOSAR 산출물 추적 지도 생성기 v3")
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="출력 폴더 (생략 시 과제 폴더 옆에 <과제명>_map 자동 생성)",
    )
    parser.add_argument(
        "--stage", choices=["0", "1", "2", "3", "4", "all"], default="all",
        help="실행할 단계 (기본 all). 0은 사전 점검, 4는 재스캔 없이 화면만 다시 그린다.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    if sys.version_info < (3, 10):
        print(
            "오류: Python 3.10 이상이 필요합니다. 현재: "
            + ".".join(map(str, sys.version_info[:3]))
        )
        return 1

    root = args.root.resolve()
    out_dir = (
        args.output.resolve()
        if args.output is not None
        else root.parent / f"{root.name}_map"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.stage not in {"0", "4"} and not root.is_dir():
        logger.error("폴더가 아닙니다: %s (--stage 0 으로 먼저 점검하세요)", root)
        return 1

    if args.stage == "all":
        stage0 = run_stage0(root, out_dir)
        if not (stage0["python_ok"] and stage0["root_ok"] and stage0["write_ok"]):
            return 1
        print()
        run_stage1(root, out_dir)
        print()
        run_stage2(root, out_dir)
        print()
        run_stage3(root, out_dir)
        print()
        run_stage4(out_dir)
    elif args.stage == "0":
        run_stage0(root, out_dir)
    elif args.stage == "1":
        run_stage1(root, out_dir)
    elif args.stage == "2":
        run_stage2(root, out_dir)
    elif args.stage == "3":
        run_stage3(root, out_dir)
    else:
        run_stage4(out_dir)

    print(f"\n출력 폴더: {out_dir}")
    return 0


# ---------------------------------------------------------------- HTML 공용

BASE_CSS = """
:root { --bg:#f5f6f8; --panel:#fff; --line:#e1e4e9; --text:#1b1f24; --muted:#6b7280;
  --accent:#2f5d8f; --chip:#eef2f7; --warn:#b45309; --bad:#dc2626;
  --c-bsw:#2f5d8f; --c-mcal:#b45309; --c-rte:#15803d; --c-lib:#7c3aed;
  --c-hdr:#64748b; --c-etc:#dc2626; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-size:14px;
  font-family:"Malgun Gothic","Segoe UI",system-ui,sans-serif; }
header { background:var(--accent); color:#fff; padding:11px 20px; }
header h1 { margin:0; font-size:16px; font-weight:600; }
header p { margin:3px 0 0; font-size:12px; opacity:.85; }
.badge { display:inline-block; background:var(--chip); border-radius:3px; padding:1px 7px;
  font-size:11px; margin-right:5px; vertical-align:middle; }
.badge.warn { background:#fef3c7; color:var(--warn); }
.badge.bad  { background:#fee2e2; color:var(--bad); }
.dot { display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:5px;
  vertical-align:baseline; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:6px;
  padding:12px 15px; margin-bottom:12px; }
.card h3 { margin:0 0 8px; font-size:12px; color:var(--accent); letter-spacing:.4px; }
.mono { font-family:Consolas,monospace; font-size:12px; word-break:break-all; }
.empty { color:var(--muted); font-style:italic; font-size:12px; }
.chips { display:flex; flex-wrap:wrap; gap:5px; }
.chip { background:var(--chip); border:1px solid var(--line); border-radius:11px;
  padding:2px 10px; font-size:12px; cursor:pointer; }
.chip:hover { background:var(--accent); color:#fff; }
.chip.dead { cursor:default; opacity:.6; }
.chip.dead:hover { background:var(--chip); color:var(--text); }
.stats { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:14px; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:6px;
  padding:9px 16px; }
.stat b { display:block; font-size:20px; }
.stat span { font-size:11px; color:var(--muted); }
input[type=text] { padding:6px 9px; border:1px solid var(--line); border-radius:5px;
  font-size:13px; }
table { border-collapse:collapse; width:100%; background:var(--panel); }
th, td { border:1px solid var(--line); padding:5px 9px; font-size:12px; text-align:left; }
th { background:var(--chip); position:sticky; top:0; }
"""


# ---------------------------------------------------------------- 단계 1 HTML

TEMPLATE_STRUCTURE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>1단계 - 폴더 구조 분석</title>
<style>
__CSS__
main { padding:16px 24px; max-width:1200px; }
details { margin:1px 0; }
summary { cursor:pointer; padding:3px 6px; border-radius:4px; font-size:13px; }
summary:hover { background:var(--chip); }
.kids { margin-left:20px; border-left:1px dotted var(--line); padding-left:8px; }
.cnt { color:var(--muted); font-size:11px; margin-left:7px; }
.legend { display:flex; flex-wrap:wrap; gap:14px; font-size:12px; margin-bottom:12px; }
</style>
</head>
<body>
<header><h1>1단계 - 폴더 구조 분석</h1><p id="meta"></p></header>
<main>
<div class="stats" id="stats"></div>
<div class="legend" id="legend"></div>
<div class="card"><h3>폴더 트리 (폴더별 파일 수 / 우세 계층 색)</h3><div id="tree"></div></div>
<div class="card" id="etcCard" style="display:none">
  <h3 style="color:var(--bad)">계층 미판정(ETC) 파일 - LAYER_RULES 점검 필요</h3>
  <div id="etcList" class="mono"></div>
</div>
<div class="card"><h3>확장자 분포</h3><div id="exts" class="mono"></div></div>
</main>
<script>
const DATA = __DATA__;
const LAYERS = __LAYERS__;
const LC = {BSW:'var(--c-bsw)',MCAL:'var(--c-mcal)',RTE_SWC:'var(--c-rte)',
            LIB:'var(--c-lib)',DEVICE_HDR:'var(--c-hdr)',ETC:'var(--c-etc)'};
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

document.getElementById('meta').textContent = DATA.root;

const files = DATA.files;
const nArx = files.filter(f=>f.ext==='.arxml').length;
const nC = files.filter(f=>f.ext==='.c').length;
const nH = files.filter(f=>f.ext==='.h').length;
const nOther = Object.values(DATA.dir_other_counts).reduce((a,b)=>a+b,0);
document.getElementById('stats').innerHTML =
  '<div class="stat"><b>'+nArx+'</b><span>ARXML</span></div>'+
  '<div class="stat"><b>'+nC+'</b><span>.c</span></div>'+
  '<div class="stat"><b>'+nH+'</b><span>.h</span></div>'+
  '<div class="stat"><b>'+nOther+'</b><span>기타 파일</span></div>';

document.getElementById('legend').innerHTML = Object.entries(DATA.layer_file_counts)
  .map(([l,c])=>'<span><span class="dot" style="background:'+LC[l]+'"></span>'+
       (LAYERS[l]||l)+' '+c+'</span>').join('');

// --- 폴더 트리 조립 ---
function newNode(name){return {name:name,dirs:{},counts:{arxml:0,c:0,h:0,other:0},layers:{}};}
const rootNode = newNode('(과제 루트)');
function getDir(path){
  let n = rootNode;
  if(!path || path==='.') return n;
  for(const seg of path.split('/')){
    if(!n.dirs[seg]) n.dirs[seg]=newNode(seg);
    n = n.dirs[seg];
  }
  return n;
}
function dirOf(p){const i=p.lastIndexOf('/');return i<0?'':p.slice(0,i);}
files.forEach(f=>{
  const d = getDir(dirOf(f.path));
  const k = f.ext==='.arxml'?'arxml':(f.ext==='.c'?'c':'h');
  d.counts[k]++;
  d.layers[f.layer]=(d.layers[f.layer]||0)+1;
});
Object.entries(DATA.dir_other_counts).forEach(([p,c])=>{ getDir(p).counts.other+=c; });

function acc(n){
  n.total = {...n.counts};
  n.layerTotal = {...n.layers};
  Object.values(n.dirs).forEach(ch=>{
    acc(ch);
    for(const k in ch.total) n.total[k]+=ch.total[k];
    Object.entries(ch.layerTotal).forEach(([k,v])=>n.layerTotal[k]=(n.layerTotal[k]||0)+v);
  });
}
acc(rootNode);

function domLayer(n){
  let best=null, bc=0;
  Object.entries(n.layerTotal).forEach(([k,v])=>{if(v>bc){bc=v;best=k;}});
  return best;
}
function cntStr(t){
  const parts=[];
  if(t.arxml) parts.push('arxml '+t.arxml);
  if(t.c) parts.push('.c '+t.c);
  if(t.h) parts.push('.h '+t.h);
  if(t.other) parts.push('기타 '+t.other);
  return parts.join(' · ')||'-';
}
function render(n, depth){
  const kids = Object.values(n.dirs).sort((a,b)=>a.name.localeCompare(b.name));
  const dl = domLayer(n);
  const dot = dl ? '<span class="dot" style="background:'+LC[dl]+'"></span>' : '';
  let html = '<details'+(depth<2?' open':'')+'><summary>'+dot+'<b>'+esc(n.name)+
    '</b><span class="cnt">'+cntStr(n.total)+'</span></summary>';
  if(kids.length){
    html += '<div class="kids">'+kids.map(k=>render(k,depth+1)).join('')+'</div>';
  }
  return html+'</details>';
}
document.getElementById('tree').innerHTML = render(rootNode, 0);

// --- ETC 경고 ---
const etc = files.filter(f=>f.layer==='ETC');
if(etc.length){
  const card=document.getElementById('etcCard');
  card.style.display='block';
  const ratio=(etc.length/files.length*100).toFixed(1);
  card.querySelector('h3').textContent =
    '계층 미판정(ETC) '+etc.length+'개 ('+ratio+'%)'+(ratio>3?' - LAYER_RULES 점검 필요':'');
  document.getElementById('etcList').innerHTML =
    etc.slice(0,60).map(f=>esc(f.path)).join('<br>')+
    (etc.length>60?'<br>... 외 '+(etc.length-60)+'개':'');
}

document.getElementById('exts').innerHTML = Object.entries(DATA.extension_counts)
  .slice(0,15).map(([e,c])=>esc(e)+' : '+c).join('<br>');
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- 단계 2 HTML

TEMPLATE_ARXML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>2단계 - ARXML 분류·해석</title>
<style>
__CSS__
main { padding:16px 24px; max-width:1300px; }
.filters { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; align-items:center; }
.filters button { border:1px solid var(--line); background:var(--panel); border-radius:11px;
  padding:3px 11px; font-size:12px; cursor:pointer; color:var(--muted); }
.filters button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.tblwrap { max-height:70vh; overflow:auto; border:1px solid var(--line); }
.k-definition{background:#dbeafe} .k-value{background:#ccfbf1} .k-swcd{background:#ede9fe}
.k-system{background:#f3f4f6} .k-unparsed{background:#fee2e2}
td.kind span{border-radius:3px;padding:1px 6px;font-size:11px;}
</style>
</head>
<body>
<header><h1>2단계 - ARXML 분류·해석</h1><p id="meta"></p></header>
<main>
<div class="stats" id="stats"></div>
<div class="card" id="unpCard" style="display:none">
  <h3 style="color:var(--bad)">해석 실패 - 정체 파악 후 SYSTEM_ARXML_RULES 보강 검토</h3>
  <div id="unpList" class="mono"></div>
</div>
<div class="filters">
  <input type="text" id="q" placeholder="경로·모듈 검색...">
  <span id="kindBtns"></span>
</div>
<div class="tblwrap"><table id="tbl">
<thead><tr><th>파일</th><th>종류</th><th>모듈 / 내용</th><th>계층</th></tr></thead>
<tbody></tbody></table></div>
</main>
<script>
const DATA = __DATA__;
const LAYERS = __LAYERS__;
const KL = {definition:'정의(BSWMD)', value:'값(ECUC)', swcd:'SWCD',
            system:'시스템', unparsed:'해석 실패'};
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

document.getElementById('meta').textContent =
  DATA.root + '  |  ARXML ' + DATA.arxml.length + '개';

document.getElementById('stats').innerHTML = Object.entries(DATA.kind_counts)
  .map(([k,c])=>'<div class="stat"><b>'+c+'</b><span>'+(KL[k]||k)+'</span></div>').join('');

const unparsed = DATA.arxml.filter(r=>r.kind==='unparsed');
if(unparsed.length){
  document.getElementById('unpCard').style.display='block';
  document.getElementById('unpList').innerHTML =
    unparsed.map(r=>esc(r.path)).join('<br>');
}

let kindFilter='ALL', q='';
const kinds=['ALL'].concat(Object.keys(DATA.kind_counts));
function renderBtns(){
  document.getElementById('kindBtns').innerHTML = kinds.map(k=>
    '<button data-k="'+k+'" class="'+(k===kindFilter?'on':'')+'">'+
    (k==='ALL'?'전체':(KL[k]||k))+'</button>').join('');
  document.querySelectorAll('#kindBtns button').forEach(b=>
    b.onclick=()=>{kindFilter=b.dataset.k; renderBtns(); renderTbl();});
}
function modCell(r){
  if(r.kind==='system') return esc(r.system_kind);
  if(r.kind==='swcd') return esc(r.module);
  if(r.kind==='unparsed') return '<span class="empty">모듈 추출 실패</span>';
  const parts=[];
  if((r.definition_modules||[]).length) parts.push('정의: '+r.definition_modules.map(esc).join(', '));
  if((r.value_modules||[]).length) parts.push('값: '+r.value_modules.map(esc).join(', '));
  if((r.referenced||[]).length) parts.push('참조 '+r.referenced.length+'건');
  return parts.join(' | ');
}
function renderTbl(){
  const rows = DATA.arxml.filter(r=>{
    if(kindFilter!=='ALL' && r.kind!==kindFilter) return false;
    if(!q) return true;
    const hay=(r.path+' '+(r.module||'')+' '+
      (r.definition_modules||[]).join(' ')+' '+(r.value_modules||[]).join(' ')).toLowerCase();
    return hay.includes(q);
  });
  document.querySelector('#tbl tbody').innerHTML = rows.map(r=>
    '<tr><td class="mono">'+esc(r.path)+'</td>'+
    '<td class="kind"><span class="k-'+r.kind+'">'+(KL[r.kind]||r.kind)+'</span></td>'+
    '<td>'+modCell(r)+'</td><td>'+(LAYERS[r.layer]||r.layer)+'</td></tr>').join('');
}
document.getElementById('q').addEventListener('input',e=>{q=e.target.value.toLowerCase();renderTbl();});
renderBtns(); renderTbl();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- 단계 3 HTML

TEMPLATE_MODULES = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>3단계 - 모듈 구성·소스 매칭</title>
<style>
__CSS__
main { padding:16px 24px; max-width:1300px; }
.bar { display:flex; height:12px; border-radius:3px; overflow:hidden; min-width:140px; }
.bar div { height:100%; }
.b-def{background:#3b82f6} .b-val{background:#14b8a6} .b-swcd{background:#8b5cf6}
.b-gen{background:#f59e0b} .b-sta{background:#94a3b8}
.legend { display:flex; gap:14px; font-size:12px; margin-bottom:12px; flex-wrap:wrap; }
tr.unused td { color:var(--muted); font-style:italic; }
.tblwrap { max-height:52vh; overflow:auto; border:1px solid var(--line); margin-bottom:14px; }
</style>
</head>
<body>
<header><h1>3단계 - 모듈 구성·소스 매칭</h1><p id="meta"></p></header>
<main>
<div class="stats" id="stats"></div>
<div class="legend">
  <span><span class="dot b-def"></span>정의 ARXML</span>
  <span><span class="dot b-val"></span>값 ARXML</span>
  <span><span class="dot b-swcd"></span>SWCD</span>
  <span><span class="dot b-gen"></span>생성 소스</span>
  <span><span class="dot b-sta"></span>정적 소스</span>
</div>
<div style="margin-bottom:10px"><input type="text" id="q" placeholder="모듈 검색...">
  <label style="font-size:12px;color:var(--muted)">
  <input type="checkbox" id="showUnused"> 미사용 모듈 표시</label></div>
<div id="sections"></div>
<div class="card" id="unmCard" style="display:none">
  <h3 style="color:var(--warn)">모듈 매칭 실패 소스</h3><div id="unmList" class="mono"></div>
</div>
<div class="card" id="susCard" style="display:none">
  <h3 style="color:var(--bad)">의심 모듈명 (오분류 가능성)</h3><div id="susList" class="mono"></div>
</div>
</main>
<script>
const DATA = __DATA__;
const LAYERS = __LAYERS__;
const LAYER_ORDER = ['BSW','MCAL','RTE_SWC','LIB','DEVICE_HDR','ETC'];
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const MODS = DATA.modules;
const names = Object.keys(MODS).sort();
const unusedNames = names.filter(n=>MODS[n].is_unused);

document.getElementById('meta').textContent = DATA.root;
document.getElementById('stats').innerHTML =
  '<div class="stat"><b>'+names.length+'</b><span>모듈</span></div>'+
  '<div class="stat"><b>'+unusedNames.length+'</b><span>미사용</span></div>'+
  '<div class="stat"><b>'+DATA.unmatched_sources.length+'</b><span>매칭 실패 소스</span></div>'+
  '<div class="stat"><b>'+DATA.unparsed_arxml.length+'</b><span>해석 실패 ARXML</span></div>';

function bar(m){
  const seg=[['b-def',m.definition_arxml.length],['b-val',m.value_arxml.length],
    ['b-swcd',m.swcd_arxml.length],['b-gen',m.generated_files.length],
    ['b-sta',m.static_files.length]];
  const total=seg.reduce((a,s)=>a+s[1],0);
  if(!total) return '<span class="empty">산출물 없음</span>';
  return '<div class="bar" title="정의 '+seg[0][1]+' / 값 '+seg[1][1]+' / SWCD '+seg[2][1]+
    ' / 생성 '+seg[3][1]+' / 정적 '+seg[4][1]+'">'+
    seg.filter(s=>s[1]).map(s=>'<div class="'+s[0]+'" style="flex:'+s[1]+'"></div>').join('')+
    '</div>';
}
function render(){
  const q=document.getElementById('q').value.toLowerCase();
  const showUnused=document.getElementById('showUnused').checked;
  let html='';
  LAYER_ORDER.forEach(layer=>{
    const list=names.filter(n=>{
      const m=MODS[n];
      if(m.layer!==layer) return false;
      if(!showUnused && m.is_unused) return false;
      return n.toLowerCase().includes(q);
    });
    if(!list.length) return;
    html+='<div class="card"><h3>'+(LAYERS[layer]||layer)+' 모듈 ('+list.length+')</h3>'+
      '<div class="tblwrap"><table><thead><tr><th>모듈</th><th>산출물 구성</th>'+
      '<th>정의</th><th>값</th><th>SWCD</th><th>생성</th><th>정적</th><th>의존</th></tr></thead><tbody>'+
      list.map(n=>{
        const m=MODS[n];
        return '<tr class="'+(m.is_unused?'unused':'')+'"><td><b>'+esc(n)+'</b>'+
          (m.is_unused?' <span class="badge warn">미사용</span>':'')+'</td>'+
          '<td>'+bar(m)+'</td><td>'+m.definition_arxml.length+'</td>'+
          '<td>'+m.value_arxml.length+'</td><td>'+m.swcd_arxml.length+'</td>'+
          '<td>'+m.generated_files.length+'</td><td>'+m.static_files.length+'</td>'+
          '<td>'+m.depends_on.length+'</td></tr>';
      }).join('')+'</tbody></table></div></div>';
  });
  document.getElementById('sections').innerHTML=html||'<p class="empty">해당 없음</p>';
}
document.getElementById('q').addEventListener('input',render);
document.getElementById('showUnused').addEventListener('change',render);
render();

if(DATA.unmatched_sources.length){
  document.getElementById('unmCard').style.display='block';
  document.getElementById('unmList').innerHTML =
    DATA.unmatched_sources.map(esc).join('<br>');
}
const sus=names.filter(n=>n.length<2 || n[0]!==n[0].toUpperCase());
if(sus.length){
  document.getElementById('susCard').style.display='block';
  document.getElementById('susList').innerHTML = sus.map(esc).join(', ');
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- 단계 4 HTML

TEMPLATE_MAP = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>AUTOSAR 산출물 지도</title>
<style>
__CSS__
.layout { display:flex; height:calc(100vh - 54px); }
.sidebar { width:250px; border-right:1px solid var(--line); background:var(--panel);
  display:flex; flex-direction:column; flex-shrink:0; }
.tools { padding:9px; border-bottom:1px solid var(--line); }
.tools input[type=text] { width:100%; }
.tabs { display:flex; flex-wrap:wrap; gap:4px; margin-top:7px; }
.tabs button { border:1px solid var(--line); background:var(--panel); border-radius:11px;
  padding:2px 9px; font-size:11px; cursor:pointer; color:var(--muted); }
.tabs button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
label.tg { display:block; margin-top:6px; font-size:11px; color:var(--muted); cursor:pointer; }
.modlist { overflow-y:auto; flex:1; }
.modlist button { display:block; width:100%; text-align:left; border:0; background:none;
  padding:5px 12px; cursor:pointer; font-size:13px; color:var(--text); }
.modlist button:hover { background:var(--chip); }
.modlist button.on { background:var(--accent); color:#fff; }
.modlist button.un { color:var(--muted); font-style:italic; }
.canvasWrap { flex:1; display:flex; flex-direction:column; min-width:0; }
.topbar { padding:7px 12px; border-bottom:1px solid var(--line); background:var(--panel);
  display:flex; gap:10px; align-items:center; font-size:12px; }
.topbar button { border:1px solid var(--line); background:var(--panel); border-radius:5px;
  padding:3px 11px; font-size:12px; cursor:pointer; }
.topbar button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
#svg { flex:1; cursor:grab; background:var(--bg); }
#svg:active { cursor:grabbing; }
.detail { width:340px; border-left:1px solid var(--line); background:var(--panel);
  overflow-y:auto; padding:14px; flex-shrink:0; }
.detail h2 { margin:0 0 4px; font-size:17px; word-break:break-all; }
.detail h4 { margin:12px 0 5px; font-size:11px; color:var(--accent); letter-spacing:.4px; }
.detail .file { font-family:Consolas,monospace; font-size:11px; word-break:break-all;
  line-height:1.7; }
.node rect { stroke-width:1.4; cursor:pointer; }
.node text { font-size:11px; font-family:"Malgun Gothic","Segoe UI",sans-serif;
  pointer-events:none; }
.node.dim { opacity:.18; }
.edge { fill:none; stroke:#d4dae2; stroke-width:1; }
.edge.dim { opacity:.12; }
.edge.dep { stroke:#d97706; stroke-width:2; }
.edge.use { stroke:#15803d; stroke-width:2; }
.fgrid { display:flex; flex-wrap:wrap; gap:3px; margin:4px 0 2px; }
.fgrid .sq { width:16px; height:16px; border-radius:3px; cursor:pointer;
  border:1px solid rgba(255,255,255,.9); }
.fgrid .sq:hover { outline:2px solid #111; }
.fgrid .sq.sel { outline:2px solid #111; }
.backlink { font-size:12px; color:var(--accent); cursor:pointer; margin-bottom:8px;
  display:inline-block; }
.hint { font-size:11px; color:var(--muted); }
</style>
</head>
<body>
<header><h1>AUTOSAR 산출물 지도</h1><p id="meta"></p></header>
<div class="layout">
  <div class="sidebar">
    <div class="tools">
      <input type="text" id="q" placeholder="모듈 검색...">
      <div class="tabs" id="tabs"></div>
      <label class="tg"><input type="checkbox" id="showUnused"> 미사용 모듈 표시</label>
    </div>
    <div class="modlist" id="list"></div>
  </div>
  <div class="canvasWrap">
    <div class="topbar">
      <button id="fitBtn">전체 화면 맞춤</button>
      <button id="edgeBtn" class="on">연결선 표시</button>
      <span class="hint">모듈 클릭: 하이라이트+상세 · 빈 곳 클릭: 해제</span>
      <span class="hint" style="margin-left:auto">
        <span class="dot" style="background:#d97706"></span>사용함(의존)
        <span class="dot" style="background:#15803d;margin-left:8px"></span>사용됨
        · 휠 확대 / 드래그 이동</span>
    </div>
    <svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg>
  </div>
  <div class="detail" id="detail"></div>
</div>
<script>
const DATA = __DATA__;
const LAYERS = __LAYERS__;
const MODS = DATA.modules, FILES = DATA.files;
const LC = {BSW:'#2f5d8f',MCAL:'#b45309',RTE_SWC:'#15803d',LIB:'#7c3aed',
            DEVICE_HDR:'#64748b',ETC:'#dc2626'};
const FC = {def:'#3b82f6',val:'#14b8a6',swcd:'#8b5cf6',gen:'#f59e0b',sta:'#94a3b8'};
const GROUPS = [
  ['def','정의 ARXML','definition_arxml'],
  ['val','값 ARXML','value_arxml'],
  ['swcd','SWCD','swcd_arxml'],
  ['gen','생성 소스','generated_files'],
  ['sta','정적 소스','static_files']];
const names = Object.keys(MODS).sort();
const byLen = [...names].sort((a,b)=>b.length-a.length);
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function matchMod(stem){
  for(const n of byLen){ if(stem===n||stem.startsWith(n+'_')) return n; }
  return null;
}
function fname(p){const i=p.lastIndexOf('/');return i<0?p:p.slice(i+1);}
function stemOf(p){const f=fname(p);const i=f.lastIndexOf('.');return i<0?f:f.slice(0,i);}

let selMod=null;            // 선택된 모듈명
let selFile=null;           // 선택된 파일 경로 (상세 패널용)
let layerFilter='ALL', showUnused=false, showEdges=true;
let POS={}, W=1400, H=900, vb=[0,0,1400,900];
const svg=document.getElementById('svg');

document.getElementById('meta').textContent =
  DATA.root + '  |  모듈 ' + names.length + '개';

// ---------- 팬/줌 ----------
function setVB(){svg.setAttribute('viewBox',vb.join(' '));}
let drag=null, moved=false;
svg.addEventListener('mousedown',e=>{drag={x:e.clientX,y:e.clientY,vb:[...vb]};moved=false;});
window.addEventListener('mousemove',e=>{
  if(!drag)return;
  if(Math.abs(e.clientX-drag.x)+Math.abs(e.clientY-drag.y)>3) moved=true;
  const r=svg.getBoundingClientRect(), s=vb[2]/r.width;
  vb[0]=drag.vb[0]-(e.clientX-drag.x)*s;
  vb[1]=drag.vb[1]-(e.clientY-drag.y)*s;
  setVB();
});
window.addEventListener('mouseup',()=>drag=null);
svg.addEventListener('click',e=>{
  if(moved) return;                       // 드래그 후 클릭은 무시
  if(e.target===svg){ selMod=null; selFile=null; paint(); renderList(); }
});
svg.addEventListener('wheel',e=>{
  e.preventDefault();
  const f=e.deltaY>0?1.15:0.87, r=svg.getBoundingClientRect();
  const mx=vb[0]+(e.clientX-r.left)/r.width*vb[2];
  const my=vb[1]+(e.clientY-r.top)/r.height*vb[3];
  vb=[mx-(mx-vb[0])*f, my-(my-vb[1])*f, vb[2]*f, vb[3]*f];
  setVB();
},{passive:false});
function fit(){
  const r=svg.getBoundingClientRect();
  const ar=r.width&&r.height ? r.width/r.height : 1.5;
  let w=W, h=H;
  if(w/h < ar) w=h*ar; else h=w/ar;
  vb=[-(w-W)/2, -(h-H)/2, w, h]; setVB();
}
document.getElementById('fitBtn').addEventListener('click',fit);

// ---------- 레이아웃 (한 번만 계산) ----------
function shownModules(){
  return names.filter(n=>{
    const m=MODS[n];
    if(!showUnused && m.is_unused) return false;
    if(layerFilter!=='ALL' && m.layer!==layerFilter) return false;
    return true;
  });
}
function layout(){
  const shown=shownModules();
  const byLevel={};
  shown.forEach(n=>{const lv=MODS[n].level||0;(byLevel[lv]=byLevel[lv]||[]).push(n);});
  const levels=Object.keys(byLevel).map(Number).sort((a,b)=>a-b);
  const colW=200, rowH=32, pad=55;
  POS={};
  let maxRows=1;
  levels.forEach((lv,i)=>{
    byLevel[lv].sort((a,b)=>(MODS[a].layer+a).localeCompare(MODS[b].layer+b));
    byLevel[lv].forEach((n,j)=>{POS[n]={x:pad+i*colW+colW/2, y:pad+j*rowH};});
    maxRows=Math.max(maxRows,byLevel[lv].length);
  });
  W=pad*2+Math.max(levels.length,1)*colW;
  H=pad*2+maxRows*rowH;
  return {shown, levels, colW, pad};
}

// ---------- 그리기 ----------
function nodeSvg(n,cls){
  const m=MODS[n], p=POS[n];
  const w=Math.max(58,n.length*7+16), h=22;
  const on=selMod===n;
  return '<g class="node'+cls+'" data-mod="'+esc(n)+'" transform="translate('+
    (p.x-w/2)+','+(p.y-h/2)+')">'+
    '<rect width="'+w+'" height="'+h+'" rx="5" fill="'+
    (on?'#fff7ed':(m.is_unused?'#f1f5f9':'#fff'))+
    '" stroke="'+(LC[m.layer]||'#94a3b8')+'"'+(on?' stroke-width="2.8"':'')+'/>'+
    '<text x="'+w/2+'" y="15" text-anchor="middle" fill="'+
    (m.is_unused?'#94a3b8':'#1b1f24')+'">'+esc(n)+'</text></g>';
}
function edgePath(a,b,cls){
  const pa=POS[a], pb=POS[b];
  if(!pa||!pb) return '';
  const dx=(pb.x-pa.x)/2;
  return '<path class="edge '+cls+'" d="M'+pa.x+' '+pa.y+
    ' C'+(pa.x+dx)+' '+pa.y+' '+(pb.x-dx)+' '+pb.y+' '+pb.x+' '+pb.y+'"/>';
}
function paint(){
  const {shown, levels, colW, pad}=layoutCache;
  const shownSet=new Set(shown);
  const nb = selMod ? new Set([selMod,
    ...MODS[selMod].depends_on, ...MODS[selMod].used_by]) : null;

  let base='', hi='';
  if(showEdges){
    shown.forEach(a=>MODS[a].depends_on.forEach(b=>{
      if(!shownSet.has(b)) return;
      if(nb && (a===selMod || b===selMod)) return;   // 강조 대상은 아래서
      base+=edgePath(a,b,nb?'dim':'');
    }));
  }
  if(selMod && shownSet.has(selMod)){
    MODS[selMod].depends_on.forEach(b=>{if(shownSet.has(b))hi+=edgePath(selMod,b,'dep');});
    MODS[selMod].used_by.forEach(a=>{if(shownSet.has(a))hi+=edgePath(a,selMod,'use');});
  }
  let nodes='';
  shown.forEach(n=>{
    const dim=nb && !nb.has(n);
    nodes+=nodeSvg(n, dim?' dim':'');
  });
  const lvLabels=levels.map((lv,i)=>'<text x="'+(pad+i*colW+colW/2)+'" y="26" '+
    'text-anchor="middle" font-size="11" fill="#9ca3af">L'+lv+(lv===0?' (드라이버)':'')+
    '</text>').join('');
  svg.innerHTML=lvLabels+base+hi+nodes;
  svg.querySelectorAll('.node').forEach(g=>{
    g.addEventListener('click',e=>{
      e.stopPropagation();
      selMod=g.dataset.mod; selFile=null;
      paint(); renderList();
    });
  });
  renderDetail();
}
let layoutCache=null;
function rebuild(keepView){
  layoutCache=layout();
  if(!keepView){ vb=[0,0,W,H]; fit(); }
  paint();
}

// ---------- 상세 패널 ----------
function chip(n){
  const ok=!!MODS[n];
  return '<span class="chip'+(ok?'':' dead')+'"'+(ok?' data-jump="'+esc(n)+'"':'')+'>'+
    esc(n)+'</span>';
}
function fileGrid(m){
  let html='';
  GROUPS.forEach(([key,label,field])=>{
    const files=m[field];
    if(!files.length) return;
    html+='<h4>'+label+' ('+files.length+')</h4><div class="fgrid">'+
      files.map(p=>'<div class="sq'+(selFile===p?' sel':'')+'" data-file="'+esc(p)+
        '" style="background:'+FC[key]+'" title="'+esc(fname(p))+'"></div>').join('')+
      '</div>';
  });
  return html || '<div class="empty">산출물 없음</div>';
}
function renderDetail(){
  const el=document.getElementById('detail');
  if(selFile){ renderFileDetail(el); return; }
  if(!selMod){
    el.innerHTML='<p class="empty">지도에서 모듈을 클릭하면 하이라이트되고,<br>'+
      '여기에 산출물(파일 노드)이 표시됩니다.</p>';
    return;
  }
  const m=MODS[selMod];
  el.innerHTML='<h2>'+esc(selMod)+'</h2>'+
    '<span class="badge" style="background:'+(LC[m.layer]||'#999')+';color:#fff">'+
    (LAYERS[m.layer]||m.layer)+'</span>'+
    (m.is_unused?'<span class="badge warn">이 과제 미사용</span>':'')+
    '<h4>사용함 (depends_on '+m.depends_on.length+')</h4>'+
    (m.depends_on.length?'<div class="chips">'+m.depends_on.map(chip).join('')+'</div>'
      :'<div class="empty">없음</div>')+
    '<h4>사용됨 (used_by '+m.used_by.length+')</h4>'+
    (m.used_by.length?'<div class="chips">'+m.used_by.map(chip).join('')+'</div>'
      :'<div class="empty">없음</div>')+
    '<div style="border-top:1px solid var(--line);margin-top:12px"></div>'+
    fileGrid(m);
  bindDetail(el);
}
function renderFileDetail(el){
  const f=FILES[selFile];
  if(!f){ el.innerHTML='<p class="empty">파일 정보 없음</p>'; return; }
  let html='<span class="backlink" id="back">← '+esc(selMod||'모듈')+' 산출물로</span>'+
    '<h2 style="font-size:14px">'+esc(fname(selFile))+'</h2>'+
    '<div class="file" style="color:var(--muted)">'+esc(selFile)+'</div>';
  if(f.type==='arxml'){
    const KL={definition:'정의 (BSWMD)',value:'값 (ECUC)',swcd:'서비스 컴포넌트 (SWCD)',
              system:'시스템 레벨',unparsed:'해석 실패'};
    html+='<h4>종류</h4><div>'+(KL[f.kind]||f.kind)+
      (f.system_kind?' - '+esc(f.system_kind):'')+'</div>';
    if((f.definition_modules||[]).length)
      html+='<h4>정의하는 모듈</h4><div class="chips">'+
        f.definition_modules.map(chip).join('')+'</div>';
    if((f.value_modules||[]).length)
      html+='<h4>값을 주는 모듈</h4><div class="chips">'+
        f.value_modules.map(chip).join('')+'</div>';
    if(f.module) html+='<h4>소속 모듈</h4><div class="chips">'+chip(f.module)+'</div>';
    if((f.referenced||[]).length)
      html+='<h4>참조하는 모듈 ('+f.referenced.length+')</h4><div class="chips">'+
        f.referenced.map(chip).join('')+'</div>';
  } else {
    html+='<h4>구분</h4><div>'+(f.generated?'생성 소스':'정적 소스')+' · '+
      (LAYERS[f.layer]||f.layer)+'</div>'+
      '<h4>소속 모듈</h4><div class="chips">'+
      (f.module?chip(f.module):'<span class="empty">매칭 실패</span>')+'</div>'+
      '<h4>#include ('+(f.includes||[]).length+')</h4>';
    if((f.includes||[]).length){
      html+='<div class="file">'+f.includes.map(inc=>{
        const t=matchMod(stemOf(inc));
        return esc(inc)+(t&&t!==f.module?'  <span class="chip" data-jump="'+esc(t)+
          '" style="font-size:10px;padding:0 7px">'+esc(t)+'</span>':'');
      }).join('<br>')+'</div>';
    } else html+='<div class="empty">없음</div>';
  }
  el.innerHTML=html;
  const back=document.getElementById('back');
  if(back) back.addEventListener('click',()=>{selFile=null; renderDetail();});
  bindDetail(el);
}
function bindDetail(el){
  el.querySelectorAll('[data-jump]').forEach(c=>
    c.addEventListener('click',()=>selectAndPan(c.dataset.jump)));
  el.querySelectorAll('[data-file]').forEach(s=>
    s.addEventListener('click',()=>{selFile=s.dataset.file; renderDetail();}));
}

// ---------- 선택 + 화면 이동 ----------
function selectAndPan(n){
  selMod=n; selFile=null;
  if(!POS[n]){   // 필터에 가려 안 보이면 필터 해제
    if(MODS[n].is_unused){showUnused=true;document.getElementById('showUnused').checked=true;}
    layerFilter='ALL'; renderTabs();
    rebuild(true);
  }
  paint(); renderList();
  if(POS[n]){ vb[0]=POS[n].x-vb[2]/2; vb[1]=POS[n].y-vb[3]/2; setVB(); }
}

// ---------- 좌측 목록 ----------
const layersInUse=['ALL'].concat(
  Object.keys(LAYERS).filter(l=>names.some(n=>MODS[n].layer===l)));
function renderTabs(){
  const box=document.getElementById('tabs'); box.innerHTML='';
  layersInUse.forEach(l=>{
    const b=document.createElement('button');
    b.textContent=l==='ALL'?'전체':(LAYERS[l]||l);
    b.className=l===layerFilter?'on':'';
    b.onclick=()=>{layerFilter=l;renderTabs();renderList();rebuild(false);};
    box.appendChild(b);
  });
}
function renderList(){
  const q=document.getElementById('q').value.toLowerCase();
  const box=document.getElementById('list'); box.innerHTML='';
  names.filter(n=>{
    const m=MODS[n];
    if(!showUnused&&m.is_unused)return false;
    if(layerFilter!=='ALL'&&m.layer!==layerFilter)return false;
    return n.toLowerCase().includes(q);
  }).forEach(n=>{
    const b=document.createElement('button');
    b.className=(selMod===n?'on ':'')+(MODS[n].is_unused?'un':'');
    b.textContent=n;
    b.onclick=()=>selectAndPan(n);
    box.appendChild(b);
  });
}
document.getElementById('q').addEventListener('input',renderList);
document.getElementById('showUnused').addEventListener('change',e=>{
  showUnused=e.target.checked; renderList(); rebuild(false);});
document.getElementById('edgeBtn').addEventListener('click',function(){
  showEdges=!showEdges; this.className=showEdges?'on':''; paint();});
window.addEventListener('resize',()=>{});

renderTabs(); renderList(); rebuild(false);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
