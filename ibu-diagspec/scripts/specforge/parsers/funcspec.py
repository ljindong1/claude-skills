"""OEM 기능사양표(.xlsx) 파서.

시트 구성: HISTORY / IBU_HW 품번사양표_<차종> / IBU_EOL 품번사양표_<차종> / RXSWIN ID
EOL 시트: 행 8~ 기능 항목(A 그룹, B 이름, C 품번코드, D TYPE), 지역군 열(헤더 행 2) 적용 표기,
          P열 '적용 기준', 오른쪽에 EOL 비트 정의.
HW 시트: 행 18~ b_xxxOption 파라미터의 VC별 값.
"""
from __future__ import annotations

import re
from pathlib import Path

import openpyxl

from ..core.projects import ProjectRegistry

APPLY_MAP = {"●": "STD", "O": "OPT", "X": "NA", "-": None}


def _norm_apply(v) -> dict:
    """셀 값을 {state, value}로. ●/O/X 외의 값은 value로 보존."""
    if v is None:
        return {"state": None, "value": None}
    s = str(v).strip()
    head = s.split("\n")[0].strip()
    if head in APPLY_MAP:
        return {"state": APPLY_MAP[head], "value": s if s != head else None}
    if head.upper() in ("ON", "OFF"):
        return {"state": "STD", "value": head.upper()}
    return {"state": "VAL", "value": s}


def parse_funcspec(path: Path, reg: ProjectRegistry) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {"file": path.name, "history": [], "features": [], "sw_params": [], "coding_fields": [], "projects": []}

    # HISTORY
    if "HISTORY" in wb.sheetnames:
        ws = wb["HISTORY"]
        for r in ws.iter_rows(min_row=3, values_only=True):
            ver, date, hist, note = (list(r) + [None] * 5)[1:5]
            if ver:
                out["history"].append({"rev": str(ver).strip(), "date": str(date or "").strip(),
                                       "contents": str(hist or "").strip(), "author": str(note or "").strip()})

    feats: dict[str, dict] = {}
    for name in wb.sheetnames:
        if "EOL" not in name or "품번사양표" not in name:
            continue
        proj = reg.code_for(name, "funcspec")
        out["projects"].append(proj)
        ws = wb[name]
        # 지역군 헤더: 행 2, E열부터 '비고' 전까지
        regions = {}
        for c in range(5, 16):
            v = ws.cell(2, c).value
            if v and str(v).strip() not in ("비고",):
                regions[c] = str(v).strip()
        group = None
        for r in range(8, ws.max_row + 1):
            a, b = ws.cell(r, 1).value, ws.cell(r, 2).value
            if a and str(a).strip() in ("HISTORY", "ISSUE"):
                break
            if a:
                group = str(a).replace("\n", " ").strip()
            if not b:
                continue
            fname = str(b).replace("\n", " ").strip()
            key = re.sub(r"\s+", " ", fname).upper()
            f = feats.setdefault(key, {
                "id": "F-" + re.sub(r"[^A-Z0-9]+", "-", key).strip("-")[:48],
                "group": group, "name": fname,
                "oem_code": str(ws.cell(r, 3).value or "").strip() or None,
                "type": str(ws.cell(r, 4).value or "").strip() or None,
                "control": str(ws.cell(r, 16).value or "").replace("\n", " ").strip() or None,
                "remark": str(ws.cell(r, 13).value or "").strip() or None,
                "applicability": {},
            })
            f["applicability"][proj] = {regions[c]: _norm_apply(ws.cell(r, c).value) for c in regions}

    out["features"] = list(feats.values())

    # SW 파라미터(HW 시트)
    for name in wb.sheetnames:
        if "HW" not in name or "품번사양표" not in name:
            continue
        proj = reg.code_for(name, "funcspec")
        ws = wb[name]
        vc_row = 4
        vcs = {c: str(ws.cell(vc_row, c).value).strip() for c in range(17, ws.max_column + 1)
               if ws.cell(vc_row, c).value}
        for r in range(18, ws.max_row + 1):
            pname = ws.cell(r, 2).value
            if not pname or not str(pname).strip().startswith("b_"):
                continue
            out["sw_params"].append({
                "name": str(pname).strip(), "module": str(ws.cell(r, 1).value or "").strip(),
                "project": proj,
                "values": {vc: str(ws.cell(r, c).value).strip() for c, vc in vcs.items() if ws.cell(r, c).value is not None},
            })
    return out
