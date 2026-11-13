"""진단사양서 정본(Raw data 워크북, master/diagspec_IBU_BCM_Master.xlsx) → parse_diagspec 과 같은 모양.

뷰어·규칙 평가(core/evaluate.py)는 이 결과를 원본 xls 파서 결과와 똑같이 다룬다.
차종별 기록값은 정본의 차종별값 격자에서 읽는다 (차종시트에 속한 차종만). 사유가 적힌 적용예외는 확인된 예외로 표시한다.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..core.projects import ProjectRegistry
from ..core.master_grid import clean
from ..core.rawdata import load
from ..core.rules import SIG
from .diagspec import S, _norm_flag, parse_security


class _Grid:
    """parse_security 에 넘길 최소한의 시트 흉내 (0 기준 행·열)."""

    def __init__(self, name: str, cells: dict[tuple[int, int], str]):
        self.name, self.cells = name, cells
        self.nrows = max((r for r, _ in cells), default=-1) + 1
        self.ncols = max((c for _, c in cells), default=-1) + 1

    def cell_value(self, r: int, c: int) -> str:
        return self.cells.get((r, c), "")


def _hist_kind(contents: str):
    m = re.search(r"\b([OX])\s*(?:->|→)\s*([OX])\b", contents)
    kind = "typo" if "오기" in contents else "flag" if m else \
        "new_project" if ("차종 추가" in contents or "항목 표시" in contents) else "other"
    return kind, m


def parse_rawbook(path: Path, reg: ProjectRegistry) -> dict:
    raw = load(path)
    m = re.match(r"diagspec_(?:IBU_)?([A-Za-z0-9]+)", Path(path).stem, re.I)
    module = m.group(1).upper() if m else ""
    for p in raw.projects:                      # 차종 표기를 별칭으로 등록 (기능사양표·블록도 쪽 이름과 맞추기 위해)
        for alias in [p["차종코드"]] + str(p.get("원본 표기", "")).split(" | "):
            if alias.strip():
                reg.code_for(alias, "diagspec")
    by_id = {it["항목ID"]: it for it in raw.items}

    items, seen_ids = [], set()
    for x in raw.items:
        kind, sheet = x["서비스"], x["시트"]
        cols = dict(spec.split(":") for spec in str(x.get("열배치", "")).split(";") if ":" in spec)
        g = lambda k: S(x.get(k, ""))
        parent = by_id.get(g("상위 항목ID"))
        did = None
        if kind == "DID":
            m = re.search(r"#(B[0-9A-F]{3})", sheet)
            did = m.group(1) if m else sheet
        name = g("이름")
        if parent and not name:                 # 하위 항목(원본의 둘째 줄 등): 상위 항목 이름을 빌린다
            name = f"{S(parent.get('이름'))} (추가 행)"
        it = {"id": f"{sheet}:{x['항목ID'] if parent or not g('코드') else g('코드')}", "kind": kind, "sheet": sheet,
              "gen": 3 if "3세대" in sheet else 2 if "2세대" in sheet else None, "did": did,
              "code": g("코드"), "name": name, "attrs": {}, "sw_variable": g("SW 변수"),
              "tool_display": g("Tool 표시"), "criteria_text": g("적용 판단 기준"), "values": [], "recorded": {}}
        a = it["attrs"]
        if parent:
            a["parent"] = parent["항목ID"]
        if kind == "RDBI":
            a["remark"] = g("Remark")
        elif kind == "DID":
            a["byte"], a["hex"] = g("Byte"), g("Hex")
            if cols.get("코드") == "0":                           # 레코드형: 코드 = 바이트 위치
                a["byte"] = a["byte"] or g("코드")
                if g("비고"):
                    a["note"] = g("비고")
            elif "bit" in cols:                                  # 비트형
                a["bit"], a["category"] = g("bit"), g("분류")
                it["name"] = g("이름") or g("분류") or name
                if g("비고"):
                    it["values"].append({"value": "", "meaning": g("비고")})
            elif g("비고") and g("비고") != it["name"]:           # 바이트형
                a["note"] = g("비고")
        elif kind == "DTC":
            a["confirmation_time"] = g("Confirmation Time")
        elif kind == "IOCBI":
            a["output_condition"], a["output_time"], a["remark"] = g("Output Condition"), g("Output Time"), g("Remark")
        elif kind == "ECUID":
            a["data_type"], a["note"], a["unece_dependent"] = g("Data Type"), g("비고"), g("UNECE 영향")
        if it["id"] in seen_ids:                # 같은 시트에 같은 코드가 또 있으면 (DID #BF01 의 두 표 등) 항목ID로 구분
            it["id"] = f"{sheet}:{x['항목ID']}"
        seen_ids.add(it["id"])
        it["values"] += [{"value": S(v.get("값")), "meaning": S(v.get("의미"))} for v in raw.values_of(x["항목ID"])]
        for code in raw.sheet_vehicles(sheet):
            f = _norm_flag(raw.value(x, code))
            if f is not None:
                it["recorded"][code] = f
        # 사유가 적힌 적용예외 = 담당자가 확인한 예외 (규칙과 달라도 불일치로 보지 않는다)
        # 규칙 입력: BCM 은 Tool 표시(원본 H열)가 품번 조건, SMK 는 'Diag Tool Display'(표출 여부)라 조건이 아니다
        it["pn_text"] = g("Tool 표시") if module != "SMK" else ""
        it["hint_signals"] = list(dict.fromkeys(s for k in ("이름", "분류", "비고", "SW 변수") for s in SIG.findall(g(k))))
        # 기록할 때의 값과 지금 격자 값이 같을 때만 확인된 예외로 본다 (나중에 값이 바뀌면 다시 검토 대상)
        conf = {c: S(e.get("사유")) for c, e in raw.exception_rows_of(x["항목ID"]).items()
                if S(e.get("사유")) and _norm_flag(clean(e.get("값"))) == it["recorded"].get(c)}
        if conf:
            it["confirmed_exceptions"] = conf
        items.append(it)

    sheets = [{"name": s, "parsed": True, "kind": next(i["서비스"] for i in raw.items if i["시트"] == s),
               "items": sum(1 for i in raw.items if i["시트"] == s), "projects": len(raw.sheet_vehicles(s)),
               "project_codes": sorted(raw.sheet_vehicles(s))} for s in raw.sheets]

    history = []
    for h in raw.history:
        contents = S(h.get("내용"))
        if not contents and not S(h.get("시트")):
            continue
        kind, m = _hist_kind(contents)
        history.append({"rev": S(h.get("Rev")), "date": S(h.get("날짜")), "author": S(h.get("작성자")),
                        "function_set": S(h.get("Function Set")), "sheet": S(h.get("시트")), "contents": contents,
                        "stage": S(h.get("단계")), "project": S(h.get("차종")), "ref": S(h.get("기준(블록도·기능사양표·SCR)")),
                        "kind": kind, "flag_from": m.group(1) if m else None, "flag_to": m.group(2) if m else None})

    sec = {(int(d["행"]) - 1, int(d["열"]) - 1): d["내용"] for d in raw.refdocs if d["문서"] == "Security Access"}
    return {"file": Path(path).name, "rev": raw.latest_rev, "history": history, "items": items, "sheets": sheets,
            "security": parse_security(_Grid("Security Access", sec)) if sec else {},
            "owners": {p["차종코드"]: p["담당자"] for p in raw.projects if p.get("담당자")}}
