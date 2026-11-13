"""담당자용 실행기 — 저장소 없이 정본 파일만으로 뷰어·엑셀을 만들고, 새 차종을 추가한다.

  python -m specforge.desk info        --master 정본.xlsx [--blockdiag 새.pdf] [--funcspec 새.xlsx]
  python -m specforge.desk build       --master 정본.xlsx [--blockdiag …] [--funcspec …] --out 저장폴더
  python -m specforge.desk add-vehicle --master 정본.xlsx --name "SU2i F/L 26MY" --like SU2I_FL_25MY
                                       [--code SU2I_FL_26MY] [--owner 이름] [--rev R392] [--author 이름]
                                       [--blockdiag …] [--funcspec …] --out 저장폴더

결과: <저장폴더>/<YYYYMMDD>/ 에 이번에 쓴 정본 사본(<정본 이름>_<날짜>.xlsx) · 뷰어 HTML · 원본양식 엑셀
      (+ 새 차종이면 확인 목록). 같은 날 다시 돌리면 덮어쓴다. 불일치 목록·요약은 실행 결과 JSON 으로만 나온다.
  python -m specforge.desk snapshot    --blockdiag 블록도.pdf --funcspec 기능사양표.xlsx … --out refdata.json   (랩: 스킬용 참조 데이터)

참조 데이터 기본값: 스킬 안의 refdata.json (없으면 저장소 input/ 의 블록도·기능사양표). 첨부한 블록도·기능사양표는 그 위에 덧붙는다
(같은 차종이면 첨부본이 우선). --alias "표기=코드" 로 문서마다 다른 차종 표기를 묶을 수 있다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # 저장소 루트 또는 스킬의 scripts/
VIEWER_NAME = "ibu_diagspec_viewer.html"


def _default_refs() -> list[Path]:
    snap = ROOT / "refdata.json"
    if snap.is_file():
        return [snap]
    return [p for p in (ROOT / "input/funcspec_CN7.xlsx", ROOT / "input/blockdiag_IBU.pdf") if p.is_file()]


def _registry(aliases: list[str]):
    from .core.projects import ProjectRegistry, _basic
    reg = ProjectRegistry.load(ROOT / "data/projects.yaml")
    for a in aliases or []:
        name, _, code = a.partition("=")
        if not code:
            raise SystemExit(f"--alias 는 '표기=코드' 형식입니다: {a}")
        reg.aliases[_basic(name)] = code.strip()
    return reg


def _refs(a) -> list[Path]:
    base = [] if a.no_default_refs else _default_refs()
    return base + [Path(p) for p in (a.funcspec or []) + (a.blockdiag or [])]


def _rev(master: Path) -> str:
    from .core.rawdata import load
    return load(master).latest_rev


def module_of(master) -> str:
    """정본 파일 이름 → 모듈 (diagspec_IBU_BCM_Master.xlsx → BCM, …_SMK_Master_20261104.xlsx → SMK)."""
    import re
    m = re.match(r"diagspec_(?:IBU_)?([A-Za-z0-9]+)", Path(master).stem, re.I)
    return m.group(1).upper() if m else ""


def _today() -> str:
    from datetime import datetime, timedelta, timezone
    return f"{datetime.now(timezone(timedelta(hours=9))):%Y%m%d}"     # 한국 날짜


def _day_dir(parent: Path) -> Path:
    """저장 폴더 = <parent>/<YYYYMMDD>/ — 같은 날 다시 돌리면 같은 폴더에 덮어쓴다."""
    d = Path(parent) / _today()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build(master: Path, refs: list[Path], day: Path, reg) -> tuple[dict, list[dict], dict[str, Path]]:
    """정본 + 참조 데이터 → 날짜 폴더에 세 가지: 정본 사본(이번에 쓴 것) · 뷰어 HTML · 원본양식 엑셀.
    불일치 목록·요약은 파일로 남기지 않고 돌려준다 (대화로 알린다)."""
    import csv
    import shutil
    import tempfile
    from .core.evaluate import build
    from .core.rawdata import load
    from .generators.excel_legacy import build_legacy
    from .generators.viewer import build_viewer
    d = _today()
    files = {"master": day / f"{Path(master).stem}_{d}.xlsx",
             "viewer": day / f"ibu_{module_of(master).lower() + '_' if module_of(master) else ''}diagspec_viewer_{d}.html",
             "legacy": day / f"진단사양서_{module_of(master) + '_' if module_of(master) else ''}원본양식_{d}.xlsx"}
    if Path(master).resolve() != files["master"].resolve():   # 먼저 날짜 폴더에 정본 사본을 두고, 그 사본으로 만든다
        shutil.copyfile(master, files["master"])           # (뷰어 머리글의 '정본' 이름이 날짜 폴더의 사본과 같도록)
    master = files["master"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        s = build(refs, master, [], tmp, None, reg=reg)
        build_viewer(tmp / "model.json", tmp / "summary.json", files["viewer"])
        with (tmp / "mismatch.csv").open(encoding="utf-8-sig") as f:
            mm = list(csv.DictReader(f))
        model = json.loads((tmp / "model.json").read_text(encoding="utf-8"))
        s["recorded_other_list"] = [f"{it['sheet']} {it['code']} {it['name'].splitlines()[0][:40]} | {p} | 값 {e['recorded']}"
                                    for it in model["diag_items"] for p, e in it["evaluation"].items()
                                    if e["status"] == "recorded_other"][:50]
    build_legacy(load(master), files["legacy"])
    return s, mm, files


def _mm_brief(mm: list[dict]) -> list[str]:
    return [f"{r['sheet']} {r['code']} {r['name'].splitlines()[0][:40]} | {r['project']} | 정본 {r['recorded']} / 규칙 {r['rule']} | {r['why']}"
            for r in mm[:50]]


def _label(v) -> str:
    """'SU2i\\nLWB | SU2i LWB' 처럼 겹친 원본 표기를 한 번씩만."""
    seen = []
    for x in str(v or "").split(" | "):
        x = " ".join(x.split())
        if x and x not in seen:
            seen.append(x)
    return " | ".join(seen)


def _summary_line(s: dict) -> dict:
    keys = ("match", "mismatch", "conditional", "exception_ok", "not_evaluable", "recorded_other", "match_rate",
            "projects_total", "projects_with_blockdiag", "projects_with_funcspec")
    return {k: s.get(k) for k in keys}


def _next_rev(rev: str) -> str:
    import re
    m = re.fullmatch(r"R(\d+)(?:\.\d+)?", rev or "")
    return f"R{int(m.group(1)) + 1}" if m else ""


def _like_candidates(code: str, raw, counts: dict, n: int = 5) -> list[dict]:
    """기준 차종 후보: 연식·개선 꼬리(25MY, FL, PE …)를 뗀 차종명이 비슷하고, 시트를 많이 가진(양산) 차종 순."""
    import difflib
    import re
    tail = re.compile(r"(?:_(?:\d{2}_?MY|FL|PE\d?|F_L|EV|HEV|PHEV|N|NLINE|N_LINE|LWB|B_BODY|수출|EXPORT|개선))+$")
    base = tail.sub("", code) or code
    full = max(counts.values(), default=1)
    out = []
    for p in raw.projects:
        c = p["차종코드"]
        if c == code:
            continue
        tok_a = {re.sub(r"^PE\d$", "PE", x) for x in code.split("_") if not re.fullmatch(r"\d{2}MY|\d+", x)}
        tok_b = {re.sub(r"^PE\d$", "PE", x) for x in c.split("_") if not re.fullmatch(r"\d{2}MY|\d+", x)}
        score = (difflib.SequenceMatcher(None, base, tail.sub("", c) or c).ratio()
                 + 0.6 * len(tok_a & tok_b) / max(len(tok_a | tok_b), 1))  # FL·LWB·PE 같은 공통 꼬리가 많을수록
        if counts.get(c, 0) < full * 0.8:                 # 일부 시트에만 있는 차종(연식 변경 등)은 기준으로 부적합
            score -= 0.5
        out.append((score, c, p))
    out.sort(reverse=True)
    return [{"code": c, "label": _label(p.get("원본 표기", "")).split(" | ")[0], "owner": p.get("담당자", ""),
             "sheets": counts.get(c, 0)} for _, c, p in out[:n]]


def cmd_info(a) -> int:
    from .core.rawdata import load
    from .core.refdata import load_sources
    reg = _registry(a.alias)
    raw = load(a.master)
    fs, bd = load_sources([p for p in _refs(a) if p.suffix.lower() in (".xlsx", ".xlsm", ".json")],
                          [p for p in _refs(a) if p.suffix.lower() == ".pdf"], reg)
    bd_codes = {e["project"]: sorted(e["variants"]) for e in bd["by_project"]}
    fs_codes = set(fs["projects"])
    counts = {}
    for s in raw.sheets:
        for c in raw.sheet_vehicles(s):
            counts[c] = counts.get(c, 0) + 1
    info = {
        "master": str(a.master), "rev": raw.latest_rev, "sheets": len(raw.sheets), "items": len(raw.items),
        "vehicles": [{"code": p["차종코드"], "label": _label(p.get("원본 표기", "")), "owner": p.get("담당자", ""),
                      "sheets": counts.get(p["차종코드"], 0), "blockdiag": bd_codes.get(p["차종코드"]),
                      "funcspec": p["차종코드"] in fs_codes} for p in raw.projects],
        # 참조 데이터에는 있는데 정본에 없는 차종 = 추가 후보 (새로 첨부한 블록도·기능사양표의 차종 코드 확인용)
        "refs_not_in_master": sorted((set(bd_codes) | fs_codes) - set(raw.project_codes) - {"통합"}),
        # 참조 데이터가 다루는 차종 — 블록도는 SMK/IMMO 형별 쪽, 기능사양표는 차종 목록 ('통합'은 블록도 공용 쪽이라 차종이 아니다)
        "blockdiag_vehicles": {c: v for c, v in bd_codes.items() if c != "통합"},
        "funcspec_vehicles": sorted(fs_codes),
        "refs": [str(p) for p in _refs(a)],
        "next_rev": _next_rev(raw.latest_rev),
    }
    if a.new_name:                                         # 새 차종 요청 준비: 코드·참조 데이터 유무·기준 차종 후보
        code = a.code or reg.code_for(a.new_name, "diagspec")
        info["new_vehicle"] = {
            "name": a.new_name, "code": code, "already_in_master": code in raw.project_codes,
            "blockdiag": bd_codes.get(code), "funcspec": code in fs_codes,
            "like_candidates": _like_candidates(code, raw, counts),
        }
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0


def cmd_build(a) -> int:
    reg = _registry(a.alias)
    day = _day_dir(Path(a.out))
    s, mm, files = _build(Path(a.master), _refs(a), day, reg)
    print(json.dumps({"out": str(day), "files": {k: str(v) for k, v in files.items()}, "rev": _rev(Path(a.master)),
                      **_summary_line(s), "mismatch_list": _mm_brief(mm),
                      "recorded_other_list": s.get("recorded_other_list", [])}, ensure_ascii=False, indent=1))
    return 0


def cmd_add_vehicle(a) -> int:
    from .core.refdata import load_sources
    from .core.vehicle_add import apply_vehicle, plan_vehicle, write_checklist
    reg = _registry(a.alias)
    refs = _refs(a)
    fs, bd = load_sources([p for p in refs if p.suffix.lower() != ".pdf"], [p for p in refs if p.suffix.lower() == ".pdf"], reg)
    plan = plan_vehicle(Path(a.master), a.name, a.like, fs, bd, reg, code=a.code)
    day = _day_dir(Path(a.out))
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:            # 새 정본은 날짜 폴더에 '<정본 이름>_<날짜>.xlsx' 로만 남긴다
        new_master = apply_vehicle(Path(a.master), Path(tmp) / Path(a.master).name, plan, owner=a.owner or "",
                                   rev=a.rev or "", author=a.author or "", note=a.note or "")
        s, mm, files = _build(new_master, refs, day, _registry(a.alias))
    mod = module_of(a.master) + "_" if module_of(a.master) else ""
    files["checklist"] = write_checklist(plan, day / f"신규차종_{mod}{plan['code']}_확인목록_{_today()}.xlsx")
    new_mm = [r for r in mm if r["project"] == plan["code"]]
    from .generators.vehicle_report import write_report
    files["report"] = write_report(plan, day / f"신규차종_{mod}{plan['code']}_추가보고_{_today()}.html", {
        "owner": a.owner or "", "rev": a.rev or "", "master_copy": files["master"].name, "viewer": files["viewer"].name,
        "legacy": files["legacy"].name, "checklist": files["checklist"].name, "variants": plan.get("variants"),
        "attachments": [Path(p).name for p in (a.blockdiag or []) + (a.funcspec or [])], "new_mismatch": new_mm})
    n = lambda f: sum(1 for r in plan["rows"] if f(r))
    print(json.dumps({
        "out": str(day), "files": {k: str(v) for k, v in files.items()}, "code": plan["code"], "like": plan["like"], "sheets": len(plan["sheets"]), "items": len(plan["rows"]),
        "by_rule": n(lambda r: r["근거"] == "규칙"),
        "by_rule_differs_from_like": n(lambda r: r["근거"] == "규칙" and r["값"] != r["기준 차종 값"]),
        "differs_from_like": [f"{r['시트']} {r['코드']} {r['이름']}: {r['기준 차종 값']}→{r['값']}" for r in plan["rows"]
                              if r["근거"] == "규칙" and r["값"] != r["기준 차종 값"]][:30],
        "needs_check": n(lambda r: "확인 필요" in r["근거"]),
        "copied_no_rule": n(lambda r: r["근거"].startswith("기준 차종 (")),
        "has_blockdiag": plan["has_blockdiag"], "has_funcspec": plan["has_funcspec"],
        "new_vehicle_mismatch": len(new_mm),          # 새 차종 칸만의 불일치 (아래 summary 는 정본 전체)
        "new_vehicle_mismatch_list": _mm_brief(new_mm),
        "summary_whole_workbook": _summary_line(s)}, ensure_ascii=False, indent=1))
    return 0


def _versions(module_dir: Path) -> list[dict]:
    """모듈 폴더의 날짜 폴더 목록 (새것부터): 날짜, Rev, 뷰어 파일."""
    import re
    from .core.rawdata import load
    out = []
    for d in sorted((p for p in Path(module_dir).iterdir() if p.is_dir() and re.fullmatch(r"\d{8}", p.name)), reverse=True):
        viewer = next(iter(sorted(d.glob("*diagspec_viewer_*.html"))), None)
        master = next(iter(sorted(d.glob("diagspec_*_Master_*.xlsx"))), None)
        if not viewer:
            continue
        try:
            rev = load(master).latest_rev if master else ""
        except Exception:
            rev = ""
        out.append({"date": d.name, "rev": rev, "viewer": str(viewer), "master": str(master) if master else ""})
    return out


def cmd_versions(a) -> int:
    """저장 루트 아래 모듈 폴더(BCM, SMK …)마다 날짜 폴더(판) 목록 — '합쳐 줘'에서 고를 판을 보여 줄 때."""
    root = Path(a.root)
    mods = {p.name: _versions(p) for p in sorted(root.iterdir()) if p.is_dir() and p.name not in ("통합",)}
    print(json.dumps({k: v for k, v in mods.items() if v}, ensure_ascii=False, indent=1))
    return 0


def cmd_combine(a) -> int:
    """모듈별 뷰어 HTML 여러 개 → 통합 뷰어 하나 (<out>/<YYYYMMDD>/ibu_diagspec_통합뷰어_<날짜>.html + 구성 기록)."""
    from .generators.combined import build_combined
    parts = []
    for spec in a.part:
        mod, _, path = spec.partition("=")
        if not path:
            raise SystemExit(f"--part 는 '모듈=뷰어 HTML 경로' 형식입니다: {spec}")
        parts.append((mod.strip().upper(), Path(path)))
    day = _day_dir(Path(a.out))
    html_path, note_path = build_combined(parts, day, _today())
    print(json.dumps({"out": str(day), "files": {"viewer": str(html_path), "note": str(note_path)},
                      "parts": [{"module": m, "viewer": str(p)} for m, p in parts]}, ensure_ascii=False, indent=1))
    return 0


def cmd_snapshot(a) -> int:
    from .core.refdata import load_sources, write_snapshot
    reg = _registry(a.alias)
    fs, bd = load_sources(a.funcspec or [], a.blockdiag or [], reg)
    p = write_snapshot(fs, bd, Path(a.out))
    print(json.dumps({"out": str(p), "bytes": p.stat().st_size, "blockdiag_vehicles": len(bd["by_project"]),
                      "funcspec_vehicles": len(fs["projects"])}, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="specforge.desk", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def refs(p, master=True):
        if master:
            p.add_argument("--master", required=True, type=Path, help="진단사양서 정본 .xlsx")
        p.add_argument("--blockdiag", nargs="*", default=[], help="블록도 PDF (참조 데이터에 덧붙음)")
        p.add_argument("--funcspec", nargs="*", default=[], help="기능사양표 .xlsx (참조 데이터에 덧붙음)")
        p.add_argument("--alias", action="append", default=[], help="'문서 표기=차종코드'")
        p.add_argument("--no-default-refs", action="store_true", help="기본 참조 데이터를 쓰지 않음")

    pi = sub.add_parser("info", help="정본 차종 목록·참조 데이터 범위 (--new-name: 새 차종 준비 정보)"); refs(pi)
    pi.add_argument("--new-name", help="추가할 새 차종 표기 — 코드·참조 데이터 유무·기준 차종 후보를 함께 낸다")
    pi.add_argument("--code", help="새 차종 코드 (기본: 표기에서 자동)")
    pb = sub.add_parser("build", help="뷰어·엑셀 양식·불일치 목록 생성"); refs(pb)
    pb.add_argument("--out", required=True, help="저장 폴더 — 안에 <YYYYMMDD>/ 를 만든다 (같은 날은 덮어씀)")
    pv = sub.add_parser("add-vehicle", help="새 차종 추가 → 새 정본·확인 목록·뷰어"); refs(pv)
    pv.add_argument("--name", required=True, help="새 차종 표기 (예: 'SU2i F/L 26MY')")
    pv.add_argument("--like", required=True, help="기준 차종 코드 (시트 구성·규칙 판단 불가 값의 출처)")
    pv.add_argument("--code", help="차종 코드 (기본: 표기에서 자동 — 블록도·기능사양표 코드와 같아야 규칙이 적용됨)")
    pv.add_argument("--owner", help="담당자")
    pv.add_argument("--rev", help="개정 번호 (예: R392)")
    pv.add_argument("--author", help="개정이력 작성자 (기본: 담당자)")
    pv.add_argument("--note", help="개정이력 메모")
    pv.add_argument("--out", required=True, help="저장 폴더 — 안에 <YYYYMMDD>/ 를 만든다 (같은 날은 덮어씀)")
    pr = sub.add_parser("versions", help="저장 루트의 모듈별 날짜 폴더(판) 목록")
    pr.add_argument("--root", required=True, help="저장 루트 (BCM·SMK 폴더가 있는 곳)")
    pc = sub.add_parser("combine", help="모듈별 뷰어 HTML → 통합 뷰어")
    pc.add_argument("--part", action="append", required=True, help="'BCM=<뷰어 HTML>' — 모듈마다 한 번씩")
    pc.add_argument("--out", required=True, help="통합 뷰어를 둘 폴더 — 안에 <YYYYMMDD>/ 를 만든다")
    ps = sub.add_parser("snapshot", help="블록도·기능사양표 → 참조 데이터 refdata.json"); refs(ps, master=False)
    ps.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        return {"info": cmd_info, "build": cmd_build, "add-vehicle": cmd_add_vehicle, "snapshot": cmd_snapshot,
                "versions": cmd_versions, "combine": cmd_combine}[a.cmd](a)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
