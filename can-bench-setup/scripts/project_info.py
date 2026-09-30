"""프로젝트 폴더에서 벤치 기본정보를 읽는다 (읽기 전용).

    python project_info.py [폴더] [--json]

폴더를 주지 않으면 지금 폴더에서 찾는다. 폴더는 저장소 루트(psu_master)여도,
그 안의 앱 폴더(psu_app)여도 된다. 앱 폴더는 아래 두 가지가 있는 폴더다.

    Configuration\\Ecu\\Mcal\\Ecud_Can.arxml
    References\\DB\\

읽는 것
    차종·제어기   References\\01_HSM_Framework\\*.sre 의 rel_<차종>_<제어기>_V
    빌드 변형     Application\\...\\PJ_Define.h 의 켜진 #define OEUK_*
    브랜치        git (있으면)
    빌드된 DB     Configuration\\System\\DBImport\\<망>_version.h 의 Path
                  (다른 PC 경로로 적혀 있어 파일 이름만 쓰고 References\\DB 에서 찾는다)
    최신 DB       References\\DB 최상위, 같은 버스면 날짜 접두사가 가장 늦은 것
    보율          Ecud_Can.arxml 컨트롤러별 BaudRate / FdBaudRate / Seg / BRS
    시험 대상     Ecud_CanNm.arxml 의 CanNmNodeId -> DB 에서 그 NM 메시지를 보내는 노드

아무것도 쓰지 않는다. 버스에 연결하지 않는다.
종료 코드: 0 읽음 / 2 앱 폴더를 못 찾음
"""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

NS = {"a": "http://autosar.org/schema/r4.0"}


# ------------------------------------------------------------ 폴더
def find_app(start: str) -> str | None:
    """start 또는 그 바로 아래에서 앱 폴더를 찾는다."""
    def is_app(d: str) -> bool:
        return (os.path.isfile(os.path.join(d, "Configuration", "Ecu", "Mcal", "Ecud_Can.arxml"))
                and os.path.isdir(os.path.join(d, "References", "DB")))

    start = os.path.abspath(start)
    if is_app(start):
        return start
    hits = [d for d in sorted(glob.glob(os.path.join(start, "*"))) if os.path.isdir(d) and is_app(d)]
    if len(hits) == 1:
        return hits[0]
    # 앱 폴더 안의 하위 폴더에서 부른 경우
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if is_app(d):
            return d
    return None


# ------------------------------------------------------------ 차종·변형
def model_ctrl(app: str) -> tuple[str | None, str | None, str | None]:
    for f in sorted(glob.glob(os.path.join(app, "References", "01_HSM_Framework", "*.sre"))):
        m = re.search(r"rel_([A-Za-z0-9]+)_([A-Za-z0-9]+)_V", os.path.basename(f))
        if m:
            return m.group(1), m.group(2), os.path.basename(f)
    return None, None, None


def variants(app: str) -> list[str]:
    hits = glob.glob(os.path.join(app, "Application", "**", "PJ_Define.h"), recursive=True)
    out = []
    for f in hits[:1]:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"\s*#define\s+(OEUK_\w+)", line)
                if m:
                    out.append(m.group(1))
    return out


def git_branch(app: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", app, "branch", "--show-current"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


# ------------------------------------------------------------ DB
def db_kind(name: str) -> str:
    if re.search(r"_FD_B2[_.]", name, re.I):
        return "B2"
    if re.search(r"_Local[_.]", name, re.I):
        return "Local"
    return "기타"


def repo_dbs(app: str) -> dict[str, list[str]]:
    d = os.path.join(app, "References", "DB")
    out: dict[str, list[str]] = {}
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith(".dbc") and os.path.isfile(os.path.join(d, fn)):
            out.setdefault(db_kind(fn), []).append(fn)
    return out


def built_dbs(app: str) -> dict[str, str]:
    """망 이름(BCAN / L1CAN) -> 빌드에 들어간 DB 파일 이름."""
    out = {}
    for f in sorted(glob.glob(os.path.join(app, "Configuration", "System", "DBImport", "*_version.h"))):
        net = os.path.basename(f)[: -len("_version.h")]
        with open(f, encoding="utf-8", errors="replace") as fh:
            m = re.search(r"Path:\s*(\S+\.dbc)", fh.read(), re.I)
        if m:
            out[net] = re.split(r"[\\/]", m.group(1))[-1]
    return out


# ------------------------------------------------------------ 보율
def _params(node: ET.Element) -> dict[str, str]:
    """컨테이너 아래 모든 파라미터. 키는 DEFINITION-REF 의 끝 두 마디."""
    out = {}
    for p in node.iter():
        if not p.tag.endswith("-PARAM-VALUE"):
            continue
        ref = p.find("a:DEFINITION-REF", NS)
        val = p.find("a:VALUE", NS)
        if ref is None or val is None or ref.text is None:
            continue
        key = "/".join(ref.text.split("/")[-2:])
        out.setdefault(key, (val.text or "").strip())
    return out


def controllers(app: str) -> list[dict]:
    path = os.path.join(app, "Configuration", "Ecu", "Mcal", "Ecud_Can.arxml")
    root = ET.parse(path).getroot()
    out = []
    for c in root.iter("{%s}ECUC-CONTAINER-VALUE" % NS["a"]):
        ref = c.find("a:DEFINITION-REF", NS)
        if ref is None or not (ref.text or "").endswith("/CanConfigSet/CanController"):
            continue
        p = _params(c)

        def i(key: str) -> int | None:
            try:
                return int(float(p[key]))
            except (KeyError, ValueError):
                return None

        def sp(prefix: str) -> float | None:
            prop, s1, s2 = (i(f"{prefix}/CanControllerPropSeg"), i(f"{prefix}/CanControllerSeg1"),
                            i(f"{prefix}/CanControllerSeg2"))
            if None in (prop, s1, s2):
                return None
            return round(100.0 * (1 + prop + s1) / (1 + prop + s1 + s2), 1)

        nom, fd = "CanControllerBaudrateConfig", "CanControllerFdBaudrateConfig"
        rate, drate = i(f"{nom}/CanControllerBaudRate"), i(f"{fd}/CanControllerFdBaudRate")
        out.append({
            "name": c.findtext("a:SHORT-NAME", namespaces=NS),
            "fd": drate is not None,
            "brs": i(f"{fd}/CanControllerTxBitRateSwitch") == 1,
            "bitrate": rate * 1000 if rate else None,
            "data_bitrate": drate * 1000 if drate else None,
            "sample_point": sp(nom),
            "data_sample_point": sp(fd),
        })
    return out


# ------------------------------------------------------------ 시험 대상
def nm_node_ids(app: str) -> list[int]:
    path = os.path.join(app, "Configuration", "Ecu", "Ecud_CanNm.arxml")
    if not os.path.isfile(path):
        return []
    root = ET.parse(path).getroot()
    ids = set()  # 채널마다 하나씩 있다. 보통 같은 값이다
    for p in root.iter():
        ref = p.find("a:DEFINITION-REF", NS)
        if ref is not None and (ref.text or "").endswith("/CanNmNodeId"):
            try:
                ids.add(int(p.findtext("a:VALUE", namespaces=NS)))
            except (TypeError, ValueError):
                pass
    return sorted(ids)


def dut_from_db(dbc_path: str, node_ids: list[int]) -> list[str]:
    """NM 메시지 ID 의 끝 바이트가 노드 번호인 메시지의 송신 노드."""
    try:
        import cantools
    except ImportError:
        return []
    try:
        db = cantools.database.load_file(dbc_path, strict=False)
    except Exception:  # noqa: BLE001 — DB 문제는 여기서 판정하지 않는다
        return []
    found = []
    for m in db.messages:
        if m.name.upper().startswith("NM_") and (m.frame_id & 0xFF) in node_ids:
            for s in m.senders:
                if s not in found:
                    found.append(s)
    return found


# ------------------------------------------------------------ 모으기
def collect(start: str) -> dict:
    app = find_app(start)
    if app is None:
        return {"app": None}
    model, ctrl, sre = model_ctrl(app)
    dbdir = os.path.join(app, "References", "DB")
    repo = repo_dbs(app)
    built = built_dbs(app)
    ctrls = controllers(app)
    ids = nm_node_ids(app)

    nets = []
    for net, fn in built.items():
        kind = db_kind(fn)
        latest = repo.get(kind, [])[-1] if repo.get(kind) else None
        path = os.path.join(dbdir, fn)
        ctrl_cfg = next((c for c in ctrls if (c["name"] or "").upper().endswith(net.upper())), None)
        nets.append({
            "net": net,
            "kind": kind,
            "built_db": fn,
            "built_db_path": path if os.path.isfile(path) else None,
            "latest_db": latest,
            "built_is_latest": fn == latest,
            "top_level_all": repo.get(kind, []),
            "controller": ctrl_cfg,
            "dut": dut_from_db(path, ids) if os.path.isfile(path) else [],
        })
    return {
        "app": app,
        "model": model,
        "controller": ctrl,
        "hsm": sre,
        "variants": variants(app),
        "branch": git_branch(app),
        "nm_node_ids": ids,
        "networks": nets,
    }


def text(info: dict) -> str:
    if not info["app"]:
        return "[못 찾음] 앱 폴더(Configuration\\Ecu\\Mcal\\Ecud_Can.arxml + References\\DB)가 없습니다."
    L = [
        f"앱 폴더   {info['app']}",
        f"차종      {info['model']}  제어기 {info['controller']}   ({info['hsm']})",
        f"빌드 변형 {', '.join(info['variants']) or '-'}",
        f"브랜치    {info['branch'] or '-'}",
        f"NM 노드   {', '.join(f'{i} (0x{i:02X})' for i in info['nm_node_ids']) or '-'}",
    ]
    for n in info["networks"]:
        c = n["controller"] or {}
        rate = "?"
        if c.get("bitrate"):
            rate = f"{c['bitrate'] // 1000}k SP {c['sample_point']}%"
            if c.get("fd"):
                rate += f" / {c['data_bitrate'] // 1000}k SP {c['data_sample_point']}%" + (" BRS" if c["brs"] else "")
        L += [
            "",
            f"[{n['net']}]  ({n['kind']})  컨트롤러 {c.get('name', '?')}",
            f"  보율      {rate}",
            f"  빌드 DB   {n['built_db']}" + ("" if n["built_db_path"] else "   [References\\DB 에 없음]"),
            f"  최신 DB   {n['latest_db']}" + ("   (= 빌드 DB)" if n["built_is_latest"] else "   [빌드 DB 와 다름]"),
            f"  시험 대상 {', '.join(n['dut']) or '-'}",
        ]
        old = [f for f in n["top_level_all"] if f != n["latest_db"]]
        if old:
            L.append(f"  최상위 옛 판 {', '.join(old)}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    as_json = "--json" in args
    rest = [a for a in args if a != "--json"]
    info = collect(rest[0] if rest else os.getcwd())
    print(json.dumps(info, ensure_ascii=False, indent=2) if as_json else text(info))
    return 0 if info["app"] else 2


if __name__ == "__main__":
    sys.exit(main())
