"""Raw 워크북 → 기존 통합 진단사양서 양식(.xlsx).

담당자에게 익숙한 원래 배치(History · Security Access · 항목 시트 31개, 항목 × 차종 격자)를 다시 만든다.
머리글 문구·열 너비·머리글 병합은 양식 정의(specforge/templates/legacy_layout.json)에서 가져온다.

- 원본에서 온 항목·값·설명은 워크북의 숨김 위치 열(원본행·열배치 등)로 원래 행에 놓는다.
- 위치가 없는 행(워크북에 새로 넣은 항목 등)은 그 시트 맨 아래에 이어 붙인다.
- 차종 열은 차종시트의 열순서대로 다시 깐다. 같은 차종이 두 번 나오던 열은 하나로 합쳐진다.
- 색으로 의미를 나타내지 않는다. 서식은 읽기 편하게 하는 용도뿐이다 (머리글 회색, 테두리, 가운데 정렬).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..core.rawdata import RawData

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "legacy_layout.json"
HEAD_FILL = PatternFill("solid", fgColor="D9D9D9")
THIN = Side(style="thin", color="A6A6A6")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
HIST_FIELDS = {5: "시트", 6: "내용", 7: "단계", 8: "차종", 9: "기준(블록도·기능사양표·SCR)"}


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _put(ws, r: int, c: int, v, align=WRAP):
    """0 기준 (r, c)에 글자로 쓴다 ('=…'도 수식이 아니라 글자)."""
    if v is None or str(v) == "":
        return None
    cell = ws.cell(r + 1, c + 1)
    cell.value = str(v)
    cell.data_type = "s"
    cell.alignment = align
    return cell


def _head(ws, sheet_t: dict, last_col: int, head_rows: int) -> None:
    for h in sheet_t.get("head", []):
        cell = _put(ws, h["r"], h["c"], h["v"], CENTER)
        if cell is not None:
            cell.font = Font(bold=True)
    for r in range(head_rows):
        for c in range(last_col + 1):
            cell = ws.cell(r + 1, c + 1)
            cell.fill = HEAD_FILL
            cell.border = BOX
    for r0, r1, c0, c1 in sheet_t.get("merges", []):
        if r1 - r0 > 1 or c1 - c0 > 1:
            ws.merge_cells(start_row=r0 + 1, end_row=r1, start_column=c0 + 1, end_column=c1)
    for c, w in sheet_t.get("widths", {}).items():
        ws.column_dimensions[get_column_letter(int(c) + 1)].width = max(4, min(w, 60))


def _item_sheet(ws, raw: RawData, t: dict, labels: dict[str, str], owners: dict[str, str]) -> None:
    st, nr = t["start_col"], t["name_row"]
    vehicles = raw.sheet_vehicles(t["name"])
    vcol = {code: st + i for i, code in enumerate(vehicles)}
    last_col = st + max(len(vehicles), 1) - 1
    _head(ws, t, last_col, nr + 1)

    # 차종 열 위 안내문('프로젝트', '(O적용, X미적용…)')은 차종 열 몇 칸에 걸쳐 병합
    span = min(len(vehicles), 8)
    for h in t.get("head", []):
        if h["c"] == st and h["r"] <= nr - 2 and span > 1:
            ws.merge_cells(start_row=h["r"] + 1, end_row=h["r"] + 1, start_column=st + 1, end_column=st + span)
    # 차종 머리글: 차종명 행 + 그 위 담당자 행 (담당자가 바뀌는 열에만 이름)
    prev = None
    for code, c in vcol.items():
        _put(ws, nr, c, labels.get(code, code), CENTER).font = Font(bold=True)
        if nr >= 1 and owners.get(code) and owners[code] != prev:
            _put(ws, nr - 1, c, owners[code], CENTER)
        prev = owners.get(code) or prev
        ws.column_dimensions[get_column_letter(c + 1)].width = 7

    items = raw.items_of(t["name"])
    placed = [_int(it.get("원본행")) for it in items]
    nxt = max([p for p in placed if p is not None] + [t["item_row"] - 1]) + 2
    defaults = t.get("default_fields") or {"코드": 0, "이름": 1}
    vdefault = t.get("value_cols") or [[st - 2, st - 1]]
    row_of = {}
    for it in items:
        r = _int(it.get("원본행"))
        if r is None:
            r, nxt = nxt, nxt + 1
            spec = defaults
        else:
            spec = dict(x.split(":") for x in str(it.get("열배치", "")).split(";") if ":" in x)
        row_of[it["항목ID"]] = r
        for k, c in spec.items():
            _put(ws, r, int(c), it.get(k, ""))
        for code, c in vcol.items():
            v = raw.value(it, code)
            if v:
                _put(ws, r, c, v, CENTER)
        # 값정의: 위치가 있으면 그 자리, 없으면 항목 행부터 아래로
        k = 0
        for v in raw.values_of(it["항목ID"]):
            vr, vc, dc = _int(v.get("원본행")), _int(v.get("값열")), _int(v.get("의미열"))
            if vr is None or vc is None:
                vr, (vc, dc) = r + k, vdefault[0]
                nxt = max(nxt, vr + 1)
            _put(ws, vr, vc, v.get("값"))
            _put(ws, vr, dc, v.get("의미"))
            k += 1
    # 항목설명: 글은 그 자리에, 메모는 칸 메모로
    for d in raw.descriptions:
        if d["항목ID"] not in row_of:
            continue
        r, c = _int(d.get("원본행")), _int(d.get("원본열"))
        if d.get("차종"):
            c = vcol.get(d["차종"], c)
        if r is None or c is None:
            continue                                   # 위치 없는 새 설명은 '단순 양식'에서 본다
        if d.get("종류") == "메모":
            cell = ws.cell(r + 1, c + 1)
            text = d["내용"] if not cell.comment else cell.comment.text + "\n" + d["내용"]
            cell.comment = Comment(text, "진단사양서")
        else:
            _put(ws, r, c, d["내용"])
    ws.freeze_panes = ws.cell(t["item_row"] + 1, st + 1)


def _history(ws, raw: RawData, t: dict) -> None:
    _head(ws, t, 9, 2)
    nxt = max([_int(h.get("원본행")) or 0 for h in raw.history] + [1]) + 1
    prev_rev = None
    for h in raw.history:
        r = _int(h.get("원본행"))
        if r is not None:
            for c, k in enumerate(["원문A", "원문Rev", "원문날짜", "원문작성자", "원문FunctionSet"]):
                _put(ws, r, c, h.get(k, ""))
        else:                                          # 새 개정: Rev·날짜·작성자는 그 Rev 첫 줄에만
            r, nxt = nxt, nxt + 1
            if h.get("Rev") != prev_rev:
                for c, k in ((1, "Rev"), (2, "날짜"), (3, "작성자"), (4, "Function Set")):
                    _put(ws, r, c, h.get(k, ""))
        prev_rev = h.get("Rev")
        for c, k in HIST_FIELDS.items():
            _put(ws, r, c, h.get(k, ""))
        if h.get("메모"):
            ws.cell(r + 1, 7).comment = Comment(str(h["메모"]), "진단사양서")
    ws.freeze_panes = "A3"


def _refdoc(ws, raw: RawData, t: dict) -> None:
    for d in raw.refdocs:
        if d["문서"] == t["name"]:
            _put(ws, int(d["행"]) - 1, int(d["열"]) - 1, d["내용"])
    for c, w in t.get("widths", {}).items():
        ws.column_dimensions[get_column_letter(int(c) + 1)].width = max(4, min(w, 80))


def template_for(raw: RawData) -> Path:
    """정본 이름의 모듈로 기존 양식 정의를 고른다: diagspec_IBU_SMK_… → legacy_layout_SMK.json, 그 밖(BCM) → legacy_layout.json."""
    import re
    m = re.match(r"diagspec_(?:IBU_)?([A-Za-z0-9]+)", Path(raw.path).stem, re.I)
    mod = m.group(1).upper() if m else ""
    alt = TEMPLATE.with_name(f"legacy_layout_{mod}.json")
    return alt if mod and mod != "BCM" and alt.is_file() else TEMPLATE


def build_legacy(raw: RawData, out: Path | str, template: Path | str | None = None) -> Path:
    T = json.loads(Path(template or template_for(raw)).read_text(encoding="utf-8"))
    labels = {p["차종코드"]: str(p.get("원본 표기", "")).split(" | ")[0] or p["차종코드"] for p in raw.projects}
    owners = {p["차종코드"]: p.get("담당자", "") for p in raw.projects}
    wb = Workbook()
    wb.remove(wb.active)
    known = set()
    for t in T["sheets"]:
        ws = wb.create_sheet(t["name"][:31])
        known.add(t["name"])
        if t["kind"] == "HISTORY":
            _history(ws, raw, t)
        elif t["kind"] == "REFDOC":
            _refdoc(ws, raw, t)
        else:
            _item_sheet(ws, raw, t, labels, owners)
    # 양식 정의에 없는 새 시트: 첫 항목 시트의 꼴을 빌려 쓴다
    base = next(t for t in T["sheets"] if t["kind"] not in ("HISTORY", "REFDOC"))
    for s in raw.sheets:
        if s not in known:
            t = {**base, "name": s, "merges": [], "default_fields": {"코드": 0, "이름": 1}}
            _item_sheet(wb.create_sheet(s[:31]), raw, t, labels, owners)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
