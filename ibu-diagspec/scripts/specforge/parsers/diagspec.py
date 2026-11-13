"""통합 진단사양서(.xls, Excel 97-2003) 파서.

모든 시트가 같은 꼴이다: 왼쪽 항목 열, 가운데 '적용 판단 기준', 오른쪽 차종 열(O/X).
시트마다 차종 열의 시작 위치·헤더 행이 달라서 머리글 텍스트로 위치를 찾는다.
"""
from __future__ import annotations

import re
from pathlib import Path

import xlrd

from ..core.projects import ProjectRegistry

ITEM_SHEET_KINDS = {
    "RDBI DataIdentifier": "RDBI",
    "DTC": "DTC",
    "IOCBI(2세대)": "IOCBI",
    "IOCBI(3세대)": "IOCBI",
    "Read ECU Identification": "ECUID",
}


def S(v) -> str:
    return str(v).replace("\xa0", " ").strip() if v is not None else ""


def _norm_flag(v) -> str | None:
    s = S(v)
    if not s:
        return None
    h = s.upper()
    if re.search(r"->|→", h):                      # 'X → O' 같은 변경 표시는 마지막 값이 현재 값 (SMK, 2026-11-03)
        last = re.findall(r"[OX]", re.split(r"->|→", h)[-1])
        if last:
            return last[0]
    if h in ("O", "X", "-"):
        return h
    if h.startswith("O"):
        return "O"
    if h.startswith("X"):
        return "X"
    return "VAL:" + s


def _find_layout(sh) -> dict | None:
    """행 0~1에서 '프로젝트/PROJECT/플랫폼' 머리글 → 차종 열 시작, 그 아래 5칸 이상 채워진 행 → 차종명 행."""
    start_col = None
    for r in (0, 1):
        for c in range(sh.ncols):
            t = S(sh.cell_value(r, c)).upper()
            if t in ("프로젝트", "PROJECT", "플랫폼", "VEHICLE MODEL"):        # VEHICLE MODEL: SMK 진단사양서
                start_col = c
                break
        if start_col is not None:
            break
    if start_col is None:
        # 'Read ECU Identification' 꼴: 프로젝트 머리글이 없고, 행 0 머리글이 끝난 다음 열부터 차종이 시작된다
        # (SMK 'IOCBI(…)-3세대CAN' 꼴: 행 0은 제목뿐이고 행 1 머리글(병합 포함)이 끝난 다음 열부터)
        heads0 = [c for c in range(sh.ncols) if S(sh.cell_value(0, c))]
        heads1 = [c for c in range(sh.ncols) if sh.nrows > 1 and S(sh.cell_value(1, c))]
        if len(heads0) <= 1 and len(heads1) > 3:
            last = heads1[-1]
            ends = [chi for rlo, rhi, clo, chi in getattr(sh, "merged_cells", []) if rlo <= 1 < rhi and clo <= last < chi]
            start_col = max(ends) if ends else last + 1
        else:
            if not heads0:
                return None
            start_col = heads0[-1] + 1
    # 차종명 행 = 시작 열 이후가 가장 많이 채워진 행 (담당자 이름 행은 드문드문 채워져 있어 제외된다)
    def _namey(v):   # 차종명으로 볼 만한 셀: O/X/V 같은 값 셀은 제외 (IOCBI(3세대)처럼 차종이 6개뿐이면 값 행이 더 많이 채워져 있다)
        t = S(v)
        return bool(t) and not re.fullmatch(r"[OXV\-]", t.upper())
    counts = {r: sum(1 for c in range(start_col, sh.ncols) if _namey(sh.cell_value(r, c))) for r in range(1, min(8, sh.nrows))}
    name_row = max(counts, key=counts.get) if counts else None
    if name_row is None or counts[name_row] < 5:
        return None
    heads = {c: S(sh.cell_value(0, c)) for c in range(start_col)}
    heads.update({c: S(sh.cell_value(1, c)) for c in range(start_col) if not heads.get(c)})

    def col_of(*keys):
        for c, h in heads.items():
            for k in keys:
                if k.lower() in h.lower():
                    return c
        return None

    return {
        "start_col": start_col, "name_row": name_row, "item_row": name_row + 1,
        "criteria_col": col_of("적용 판단 기준", "적용판단", "검토 방법"),
        "tool_col": col_of("Diag", "Tool"),
        "desc_col": col_of("Description", "Trouble description", "Control By", "Parameter"),
        "swvar_col": col_of("내부변수", "Function set"),
        # DID 시트 두 가지 꼴: 바이트형(Description·User Option Value…)과 비트형(bit·Description=Input/Output·이름·Remark)
        "bit_col": next((c for c, h in heads.items() if h.lower() == "bit"), None),
        "remark_col": col_of("Remark"),
        "value_col": col_of("User Option Value", "Value"),
    }


def _projects(sh, lay, reg: ProjectRegistry, sheet: str) -> dict[int, str]:
    cols = {}
    for c in range(lay["start_col"], sh.ncols):
        n = S(sh.cell_value(lay["name_row"], c))
        if n and n not in ("…", "...") and not re.fullmatch(r"[OXV\-]", n.upper()):   # 'O'/'V' 같은 값 셀이 머리글 행에 섞인 경우 제외
            cols[c] = reg.code_for(n, "diagspec")
    return cols


def _owners(sh, lay, pcols: dict[int, str]) -> dict[str, str]:
    """차종명 행 바로 위 행의 담당자 이름. 이름은 구간 시작 열에만 적혀 있고 다음 이름까지 이어진다."""
    r = lay["name_row"] - 1
    if r < 0:
        return {}
    out, cur = {}, ""
    for c in range(lay["start_col"], sh.ncols):
        v = S(sh.cell_value(r, c))
        if v and not v.startswith("(") and len(v) <= 10:
            cur = v
        if c in pcols and cur:
            out[pcols[c]] = cur
    return out


def parse_history(sh) -> list[dict]:
    rows, cur = [], {}
    for r in range(2, sh.nrows):
        rev = S(sh.cell_value(r, 1))
        if rev and not re.fullmatch(r"R\d+(\.\d+)?", rev):   # History 11행처럼 다른 시트 행이 잘못 붙여진 경우: 개정 번호로 보지 않는다
            rev = ""
        if rev:
            d = S(sh.cell_value(r, 2)).replace(".0", "")
            if re.fullmatch(r"\d{6}", d):                       # yymmdd 로 적은 경우 (대부분)
                date = f"20{d[0:2]}-{d[2:4]}-{d[4:6]}"
            elif re.fullmatch(r"\d{5}", d):                     # 엑셀 날짜 일련번호(45147 등)로 들어온 경우
                date = xlrd.xldate.xldate_as_datetime(int(d), sh.book.datemode).strftime("%Y-%m-%d")
            else:
                date = d
            cur = {"rev": rev, "date": date, "author": S(sh.cell_value(r, 3)), "function_set": S(sh.cell_value(r, 4))}
        contents = S(sh.cell_value(r, 6))
        if not contents and not S(sh.cell_value(r, 5)):
            continue
        m = re.search(r"\b([OX])\s*(?:->|→)\s*([OX])\b", contents)
        rows.append({**cur, "sheet": S(sh.cell_value(r, 5)), "contents": contents,
                     "stage": S(sh.cell_value(r, 7)), "project": S(sh.cell_value(r, 8)), "ref": S(sh.cell_value(r, 9)),
                     "kind": ("typo" if "오기" in contents else "flag" if m else
                              "new_project" if ("차종 추가" in contents or "항목 표시" in contents) else "other"),
                     "flag_from": m.group(1) if m else None, "flag_to": m.group(2) if m else None})
    return rows


def parse_security(sh) -> dict:
    """Security Access 시트는 항목×차종 표가 아니라 설명문·소표 묶음이다. 빈 행으로 블록을 나눠 셀을 그대로 담는다."""
    blocks, cur = [], None
    for r in range(sh.nrows):
        cells = [S(sh.cell_value(r, c)) for c in range(sh.ncols)]
        while cells and not cells[-1]:
            cells.pop()
        if not cells:
            cur = None
            continue
        if cur is None:
            cur = {"rows": []}
            blocks.append(cur)
        cur["rows"].append(cells)
    for b in blocks:                      # 첫 행이 셀 하나뿐이면 제목으로 뺀다
        if len(b["rows"]) > 1 and sum(1 for c in b["rows"][0] if c) == 1:
            b["title"] = next(c for c in b["rows"][0] if c)
            b["rows"] = b["rows"][1:]
    return {"sheet": sh.name, "blocks": blocks}


def parse_diagspec(path: Path, reg: ProjectRegistry) -> dict:
    wb = xlrd.open_workbook(str(path))
    out = {"file": path.name, "history": [], "items": [], "sheets": [], "security": {}, "owners": {}}
    owner_votes: dict[str, dict[str, int]] = {}
    for sh in wb.sheets():
        if sh.name == "History":
            out["history"] = parse_history(sh)
            continue
        if sh.name == "Security Access":
            out["security"] = parse_security(sh)
            continue
        lay = _find_layout(sh)
        if not lay:
            out["sheets"].append({"name": sh.name, "parsed": False})
            continue
        pcols = _projects(sh, lay, reg, sh.name)
        for code, who in _owners(sh, lay, pcols).items():
            owner_votes.setdefault(code, {})[who] = owner_votes.setdefault(code, {}).get(who, 0) + 1
        kind = ITEM_SHEET_KINDS.get(sh.name) or ("WDBI" if sh.name.startswith("WDBI") else "DID" if sh.name.startswith("DID") else "OTHER")
        gen = 3 if "3세대" in sh.name else 2 if "2세대" in sh.name else None
        did = None
        if kind == "DID":
            m = re.search(r"#(B[0-9A-F]{3})", sh.name)
            did = m.group(1) if m else sh.name
        n_items = 0
        cur = None
        for r in range(lay["item_row"], sh.nrows):
            c0, c1 = S(sh.cell_value(r, 0)), S(sh.cell_value(r, 1))
            is_item = False
            c2 = S(sh.cell_value(r, 2))
            if kind == "DID":   # PID형(B열 0x..) 또는 레코드형(#BE01 등: A열 '#4', C열 'XX')
                is_item = c1.lower().startswith("0x") or (c0.startswith("#") and c2.upper().startswith("XX"))
            elif kind == "WDBI":  # 값형(0x..) 또는 바이트 위치형(WDBI-0402/12AA: '#4~#7', 'XX~XX')
                is_item = bool(re.fullmatch(r"0x[0-9A-Fa-f]{2}", c0)) or (c0.startswith("#") and c2.upper().startswith("XX"))
            else:
                is_item = bool(c0) and c0 not in ("Hex Value",) and not c0.startswith("※")
            if is_item:
                code = (c1 if kind == "DID" else c0)
                desc_col = lay["desc_col"] if lay["desc_col"] is not None else (3 if kind == "DID" else 1)
                cur = {
                    "id": f"{sh.name}:{code}", "kind": kind, "sheet": sh.name, "gen": gen, "did": did,
                    "code": code, "name": S(sh.cell_value(r, desc_col)),
                    "attrs": {},
                    "sw_variable": S(sh.cell_value(r, lay["swvar_col"])) if lay["swvar_col"] is not None else "",
                    "tool_display": S(sh.cell_value(r, lay["tool_col"])) if lay["tool_col"] is not None else "",
                    "criteria_text": S(sh.cell_value(r, lay["criteria_col"])) if lay["criteria_col"] is not None else "",
                    "values": [],
                    "recorded": {},
                }
                if kind == "RDBI":
                    cur["attrs"]["remark"] = S(sh.cell_value(r, 2))          # 'Byte frame' 등
                if kind == "DID":
                    cur["attrs"]["byte"] = S(sh.cell_value(r, 0))            # dataRecord 바이트 위치 '#4'
                    cur["attrs"]["hex"] = S(sh.cell_value(r, 2))
                    if not c1.lower().startswith("0x"):                        # 레코드형(#BE01 등): 코드 = 바이트 위치, 이름 = Description
                        cur["code"] = c0
                        cur["id"] = f"{sh.name}:{c0}"
                        rem = S(sh.cell_value(r, lay["remark_col"])) if lay["remark_col"] is not None else ""
                        if rem:
                            cur["attrs"]["note"] = rem
                    elif lay["bit_col"] is not None:                           # 비트형: bit | 분류(Input/Output) | 이름 | Remark
                        cur["attrs"]["bit"] = S(sh.cell_value(r, lay["bit_col"]))
                        cur["attrs"]["category"] = S(sh.cell_value(r, desc_col))
                        cur["name"] = S(sh.cell_value(r, desc_col + 1)) or cur["name"]
                        rem = S(sh.cell_value(r, lay["remark_col"])) if lay["remark_col"] is not None else ""
                        if rem:
                            cur["values"].append({"value": "", "meaning": rem})
                    else:                                                      # 바이트형: 설명 보조(E열)
                        note = S(sh.cell_value(r, desc_col + 1))
                        if note and note != cur["name"]:
                            cur["attrs"]["note"] = note
                if kind == "DTC":
                    cur["attrs"]["confirmation_time"] = S(sh.cell_value(r, 2))
                if kind == "IOCBI":
                    cur["attrs"]["output_condition"] = S(sh.cell_value(r, 2))
                    cur["attrs"]["output_time"] = S(sh.cell_value(r, 3))
                    cur["attrs"]["remark"] = S(sh.cell_value(r, 4))
                if kind == "ECUID":
                    cur["attrs"]["data_type"] = S(sh.cell_value(r, 2))
                    cur["attrs"]["note"] = S(sh.cell_value(r, 3))
                    cur["attrs"]["unece_dependent"] = S(sh.cell_value(r, 4))
                for c, p in pcols.items():
                    f = _norm_flag(sh.cell_value(r, c))
                    if f is not None:
                        cur["recorded"][p] = f
                out["items"].append(cur)
                n_items += 1
            # 값 열거(DID: F/G열, WDBI: C/D열) — 항목 아래 이어지는 행
            if cur is not None and (kind == "WDBI" or (kind == "DID" and lay["bit_col"] is None)):
                cands = [(5, 6)] if kind == "DID" else [(2, 3), (4, 5)]   # WDBI-12AA 는 값이 E/F열에 있다
                for vc, dc in cands:
                    v, d = S(sh.cell_value(r, vc)), S(sh.cell_value(r, dc))
                    if v and (v.lower().startswith("0x") or v.lower().startswith("not")):
                        cur["values"].append({"value": v, "meaning": d})
                        break
        out["sheets"].append({"name": sh.name, "parsed": True, "kind": kind, "items": n_items,
                              "projects": len(pcols), "project_codes": sorted(set(pcols.values()))})
    out["owners"] = {code: max(v, key=v.get) for code, v in owner_votes.items()}   # 시트마다 다르면 다수결
    return out
