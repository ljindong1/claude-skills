"""참조 데이터(블록도·기능사양표) 읽기·합치기·스냅숏.

규칙 평가에 쓰는 블록도(PDF)·기능사양표(.xlsx)는 여러 개를 받을 수 있다.
  - .pdf  → 블록도 파서,  .xlsx → 기능사양표 파서
  - .json → 미리 뽑아 둔 스냅숏(refdata.json: {"funcspec": …, "blockdiag": …}). 담당자용 스킬은 19MB 블록도 PDF 대신 이걸 싣는다.
여러 출처는 앞에서 뒤로 합친다. 같은 차종이 뒤 출처에 있으면 뒤 출처가 그 차종을 통째로 대신한다
(새 블록도 개정본·새 차종 기능사양표를 첨부하면 그 차종은 첨부본 기준으로 계산된다).
"""
from __future__ import annotations

import json
from pathlib import Path

from .projects import ProjectRegistry


def _empty_fs() -> dict:
    return {"file": "", "history": [], "features": [], "sw_params": [], "coding_fields": [], "projects": []}


def _empty_bd() -> dict:
    return {"file": "", "pages": [], "history_pages": [], "by_project": [], "signals": []}


def _merge_fs(base: dict, new: dict) -> dict:
    over = set(new.get("projects") or [])
    feats = []
    for f in base["features"]:
        app = {p: v for p, v in f["applicability"].items() if p not in over}
        if app:
            feats.append({**f, "applicability": app})
    return {
        "file": " + ".join(x for x in (base["file"], new.get("file", "")) if x),
        "history": base["history"] + list(new.get("history") or []),
        "features": feats + list(new.get("features") or []),
        "sw_params": [s for s in base["sw_params"] if s.get("project") not in over] + list(new.get("sw_params") or []),
        "coding_fields": base["coding_fields"] + list(new.get("coding_fields") or []),
        "projects": [p for p in base["projects"] if p not in over] + list(new.get("projects") or []),
    }


def _merge_bd(base: dict, new: dict) -> dict:
    over = {e["project"] for e in new.get("by_project") or []}
    by = [e for e in base["by_project"] if e["project"] not in over] + list(new.get("by_project") or [])
    pages = [p for p in base["pages"] if p["project"] not in over] + list(new.get("pages") or [])
    return {
        "file": " + ".join(x for x in (base["file"], new.get("file", "")) if x),
        "pages": pages,
        "history_pages": base["history_pages"] + list(new.get("history_pages") or []),
        "by_project": by,
        "signals": sorted({s for e in by for s in e["signals"]}),
    }


def _register(reg: ProjectRegistry, fs: dict | None, bd: dict | None) -> None:
    """스냅숏에서 읽은 차종 코드·표기를 별칭표에 다시 올린다 (파서로 읽을 때와 같은 상태가 되도록)."""
    for p in (fs or {}).get("projects") or []:
        reg.code_for(p, "funcspec")
    for pg in (bd or {}).get("pages") or []:          # 스냅숏의 차종 코드를 그대로 쓰고, 쪽 제목 표기는 그 코드의 별칭으로 남긴다
        reg.code_for(pg["project"], "blockdiag")
        if pg.get("project_raw"):
            reg.codes[pg["project"]]["aliases"].add(pg["project_raw"])


def as_list(x) -> list[Path]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [Path(p) for p in x]
    return [Path(x)]


def load_sources(funcspecs, blockdiags, reg: ProjectRegistry) -> tuple[dict, dict]:
    """funcspecs·blockdiags: 경로 하나 또는 목록 (.xlsx/.pdf/.json 섞어도 됨). 반환 (기능사양표, 블록도) 합친 결과."""
    fs, bd = _empty_fs(), _empty_bd()
    for p in as_list(funcspecs) + as_list(blockdiags):
        suf = p.suffix.lower()
        if suf == ".json":
            snap = json.loads(p.read_text(encoding="utf-8"))
            _register(reg, snap.get("funcspec"), snap.get("blockdiag"))
            if snap.get("funcspec"):
                fs = _merge_fs(fs, snap["funcspec"])
            if snap.get("blockdiag"):
                bd = _merge_bd(bd, snap["blockdiag"])
        elif suf in (".xlsx", ".xlsm"):
            from ..parsers.funcspec import parse_funcspec
            fs = _merge_fs(fs, parse_funcspec(p, reg))
        elif suf == ".pdf":
            from ..parsers.blockdiag import parse_blockdiag
            bd = _merge_bd(bd, parse_blockdiag(p, reg))
        else:
            raise ValueError(f"블록도(.pdf)·기능사양표(.xlsx)·스냅숏(.json)이 아닙니다: {p}")
    return fs, bd


def write_snapshot(fs: dict, bd: dict, path: Path) -> Path:
    """규칙 평가에 필요한 부분만 남긴 스냅숏 (블록도 쪽 history 텍스트는 뺀다)."""
    snap = {"funcspec": fs, "blockdiag": {k: v for k, v in bd.items() if k != "history"}}
    Path(path).write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return Path(path)
