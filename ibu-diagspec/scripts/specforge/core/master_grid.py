"""정본의 '차종별값' 격자 시트 (항목 × 차종) 쓰기·전환.

정본 구조 (2026-11-03 변경):
  - 차종별 O/X 는 '차종별값' 시트 한 장에 둔다. 행 = 진단항목, 열 = 차종 — 담당자가 익숙한 원래 엑셀 모양이다.
    그 차종이 항목의 시트에 속하지 않는 칸(차종시트에 없음)은 회색이며 값이 없다.
  - '적용예외' 시트는 규칙과 다르지만 담당자가 확인한 칸만 둔다 (사유·근거·확인자·확인일).
  - 진단항목의 '기본 적용' 열은 없앤다 (예전 구조에서 '가장 많은 값 + 다른 칸은 적용예외'로 값을 줄여 적던 방식).
값은 보이지 않는 공백(\\xa0 등)을 걷어 낸 글자로 적는다.
"""
from __future__ import annotations

from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

GRID = "차종별값"
FIXED = ["항목ID", "시트", "코드", "이름"]
EXC_COLS = ["항목ID", "차종", "값", "사유", "근거(Rev·CR)", "확인자", "확인일"]
HEAD_FILL = PatternFill("solid", fgColor="0E7490")
NA_FILL = PatternFill("solid", fgColor="D9D9D9")


def clean(v) -> str:
    """보이지 않는 공백을 걷어 낸 값 ('O\\xa0' → 'O'). '(빈칸)' 표시는 빈 값으로."""
    s = str(v if v is not None else "").replace("\xa0", " ").strip()
    return "" if s == "(빈칸)" else s


def vehicle_order(sheets: list[str], membership: list[dict]) -> list[str]:
    """원본 열 순서: 시트 순서대로 그 시트의 열순서를 따라 처음 나온 차종부터."""
    by_sheet: dict[str, list] = {}
    for m in membership:
        by_sheet.setdefault(m["시트"], []).append((int(m.get("열순서") or 10**6), m["차종코드"]))
    order: list[str] = []
    for s in list(sheets) + [s for s in by_sheet if s not in sheets]:
        for _, c in sorted(by_sheet.get(s, [])):
            if c not in order:
                order.append(c)
    return order


def _text(cell, v) -> None:
    cell.value, cell.data_type, cell.number_format = str(v), "s", "@"


def style_grid(ws, n_rows: int, n_codes: int) -> None:
    for j in range(1, len(FIXED) + n_codes + 1):
        c = ws.cell(1, j)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), HEAD_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True,
                                text_rotation=90 if j > len(FIXED) else 0)
    ws.row_dimensions[1].height = 110
    for j, w in enumerate([20, 22, 10, 40], 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    for j in range(len(FIXED) + 1, len(FIXED) + n_codes + 1):
        ws.column_dimensions[get_column_letter(j)].width = 4.5
    ws.freeze_panes = ws.cell(2, len(FIXED) + 1)
    last = get_column_letter(len(FIXED) + n_codes)
    ws.auto_filter.ref = f"A1:{last}{n_rows + 1}"
    ws.data_validations.dataValidation = []
    dv = DataValidation(type="list", formula1='"O,X,-"', allow_blank=True, errorStyle="warning", showErrorMessage=True,
                        errorTitle="O/X 가 아닌 값", error="보통은 O·X·- 중 하나입니다. 값형 항목이면 그대로 두셔도 됩니다.")
    dv.add(f"{get_column_letter(len(FIXED) + 1)}2:{last}{n_rows + 1}")
    ws.add_data_validation(dv)


def write_grid(wb, items: list[dict], codes: list[str], member: dict[str, set], values: dict[tuple[str, str], str]):
    """wb 에 '차종별값' 시트를 (다시) 만든다. items: 진단항목 행, member: 시트 → 차종 집합."""
    if GRID in wb.sheetnames:
        del wb[GRID]
    ws = wb.create_sheet(GRID, index=wb.sheetnames.index("진단항목") + 1 if "진단항목" in wb.sheetnames else None)
    for j, h in enumerate(FIXED + codes, 1):
        _text(ws.cell(1, j), h)
    for i, it in enumerate(items, 2):
        name = str(it.get("이름") or "").split("\n")[0] or (f"↳ {it['상위 항목ID']} 추가 행" if it.get("상위 항목ID") else "")
        for j, v in enumerate([it["항목ID"], it["시트"], it.get("코드", ""), name], 1):
            if v not in (None, ""):
                _text(ws.cell(i, j), v)
        mem = member.get(it["시트"], set())
        for j, code in enumerate(codes, len(FIXED) + 1):
            cell = ws.cell(i, j)
            if code not in mem:
                cell.fill = NA_FILL
                continue
            v = clean(values.get((it["항목ID"], code), ""))
            if v:
                _text(cell, v)
                cell.alignment = Alignment(horizontal="center")
    style_grid(ws, len(items), len(codes))
    return ws


def write_exceptions(wb, rows: list[dict]) -> None:
    """'적용예외' 시트를 확인된 예외만으로 다시 쓴다."""
    idx = wb.sheetnames.index("적용예외") if "적용예외" in wb.sheetnames else None
    if idx is not None:
        del wb["적용예외"]
    ws = wb.create_sheet("적용예외", index=idx)
    for j, h in enumerate(EXC_COLS, 1):
        c = ws.cell(1, j, h)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), HEAD_FILL
    for i, r in enumerate(rows, 2):
        for j, h in enumerate(EXC_COLS, 1):
            v = r.get(h)
            if v not in (None, ""):
                _text(ws.cell(i, j), clean(v) if h == "값" else v)
    for j, w in enumerate([22, 18, 6, 50, 34, 10, 12], 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G{max(len(rows) + 1, 2)}"


def drop_default_column(wb) -> None:
    """진단항목의 '기본 적용' 열을 지우고 목록 검사를 다시 건다 (열이 당겨지므로)."""
    ws = wb["진단항목"]
    head = [c.value for c in ws[1]]
    if "기본 적용" not in head:
        return
    ws.delete_cols(head.index("기본 적용") + 1)
    head = [c.value for c in ws[1]]
    ws.data_validations.dataValidation = []
    n = ws.max_row + 500
    for col, formula in (("서비스", "=코드표!$A$2:$A$7"), ("시트", None)):
        if col not in head:
            continue
        letter = get_column_letter(head.index(col) + 1)
        if formula is None:
            k = wb["코드표"]
            last = max((r for r in range(2, k.max_row + 1) if k.cell(r, 6).value), default=2)
            formula = f"=코드표!$F$2:$F${last}"
        dv = DataValidation(type="list", formula1=formula, allow_blank=True, errorStyle="warning", showErrorMessage=True,
                            errorTitle="목록에 없는 값", error="코드표의 값을 쓰는 것이 원칙입니다. 그대로 둘까요?")
        dv.add(f"{letter}2:{letter}{n}")
        ws.add_data_validation(dv)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(head))}{ws.max_row}"


def migrate(src, dst) -> dict:
    """예전 구조(기본 적용 + 적용예외 전체) 정본 → 새 구조(차종별값 격자 + 확인된 예외만)."""
    from openpyxl import load_workbook
    from .rawdata import load
    raw = load(src)
    wb = load_workbook(src)
    member = {s: set(raw.sheet_vehicles(s)) for s in raw.sheets}
    codes = vehicle_order(raw.sheets, raw.membership)
    codes += [c for c in raw.project_codes if c not in codes]
    values = {}
    for it in raw.items:
        for c in member.get(it["시트"], ()):
            values[(it["항목ID"], c)] = raw.value(it, c) or ""
    write_grid(wb, raw.items, codes, member, values)
    kept = [e for e in raw.exception_rows.values() if str(e.get("사유") or "").strip()]
    write_exceptions(wb, kept)
    drop_default_column(wb)
    wb.save(dst)
    return {"items": len(raw.items), "vehicles": len(codes), "cells": sum(len(member.get(i["시트"], ())) for i in raw.items),
            "exceptions_before": len(raw.exception_rows), "exceptions_kept": len(kept)}
