"""Raw 워크북 → 단순 양식 엑셀(.xlsx).

기존 양식과 같은 내용을, 시트 31개 대신 몇 장의 표로 모아 정렬·필터하기 쉽게 만든다.

  적용표   : 항목 1행 × 차종 열. 그 시트에 속하지 않는 차종 칸은 회색(값 없음)
  항목상세 : 항목 1행. 필드 + 값 정의 + 설명을 한 행에
  차종     : 차종 1행. 표기·담당자·속한 시트 수
  개정이력 : 변경 1행
  Security Access : 참고문서 원문
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..core.rawdata import RawData

HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
NA_FILL = PatternFill("solid", fgColor="E7E6E6")
HEAD_FONT = Font(bold=True, color="FFFFFF")
CENTER = Alignment(horizontal="center", vertical="center")
WRAP = Alignment(wrap_text=True, vertical="top")
DETAIL_FIELDS = ["코드", "이름", "Byte", "bit", "분류", "Hex", "적용 판단 기준", "Tool 표시", "SW 변수", "Remark", "비고",
                 "Confirmation Time", "Output Condition", "Output Time", "Data Type", "UNECE 영향"]


def _text(cell, v):
    cell.value = str(v)
    cell.data_type = "s"


def _table(ws, cols: list[str], rows: list[list], widths: dict[str, float] | None = None, freeze: str = "B2") -> None:
    for j, name in enumerate(cols, 1):
        cell = ws.cell(1, j, name)
        cell.font, cell.fill, cell.alignment = HEAD_FONT, HEAD_FILL, Alignment(vertical="center", wrap_text=True)
    for i, row in enumerate(rows, 2):
        for j, v in enumerate(row, 1):
            if v not in (None, ""):
                _text(ws.cell(i, j), v)
                ws.cell(i, j).alignment = WRAP
    for j, name in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(name, max(10, min(30, len(name) * 2 + 4)))
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(len(rows) + 1, 2)}"


def build_simple(raw: RawData, out: Path | str) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "읽어보기"
    for line in [
        "진단사양서 — 단순 양식 (자동 생성본)",
        "",
        f"이 파일은 Raw 워크북 `{raw.path.name}` 에서 자동으로 만든 결과물입니다. 여기서 고치지 말고 워크북을 고칩니다.",
        "적용표: 항목 × 차종 O/X. 회색 칸은 그 차종이 해당 시트에 속하지 않아 값이 없는 칸입니다.",
        "항목상세: 항목의 필드·값 정의·설명을 한 행에 모았습니다.",
    ]:
        ws.append([line])
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 110

    # 적용표
    codes = raw.project_codes
    wt = wb.create_sheet("적용표")
    fixed = ["시트", "항목ID", "코드", "이름"]
    for j, name in enumerate(fixed + codes, 1):
        cell = wt.cell(1, j, name)
        cell.font, cell.fill = HEAD_FONT, HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True, text_rotation=90 if j > len(fixed) else 0)
    wt.row_dimensions[1].height = 90
    for i, it in enumerate(raw.items, 2):
        name = it.get("이름") or (f"↳ {it['상위 항목ID']} 추가 행" if it.get("상위 항목ID") else "")
        for j, v in enumerate([it["시트"], it["항목ID"], it.get("코드", ""), name], 1):
            if v:
                _text(wt.cell(i, j), v)
        for j, code in enumerate(codes, len(fixed) + 1):
            v = raw.value(it, code)
            cell = wt.cell(i, j)
            if v is None:
                cell.fill = NA_FILL
            elif v:
                _text(cell, v)
                cell.alignment = CENTER
    for j, w in enumerate([24, 22, 12, 45], 1):
        wt.column_dimensions[get_column_letter(j)].width = w
    for j in range(len(fixed) + 1, len(fixed) + len(codes) + 1):
        wt.column_dimensions[get_column_letter(j)].width = 4.5
    wt.freeze_panes = wt.cell(2, len(fixed) + 1)
    wt.auto_filter.ref = f"A1:{get_column_letter(len(fixed) + len(codes))}{len(raw.items) + 1}"

    # 항목상세 (값이 하나도 없는 필드 열은 뺀다)
    vals, descs = defaultdict(list), defaultdict(list)
    for v in raw.values:
        vals[v["항목ID"]].append(f"{v.get('값', '')} : {v.get('의미', '')}".strip(" :"))
    for d in sorted(raw.descriptions, key=lambda d: (d["항목ID"], int(d.get("순서") or 0))):
        tag = "[메모] " if d.get("종류") == "메모" else ""
        who = f"({d['차종']}) " if d.get("차종") else ""
        descs[d["항목ID"]].append(f"{tag}{who}{d['내용']}")
    fields = [f for f in DETAIL_FIELDS if any(it.get(f) for it in raw.items)]
    cols = ["시트", "항목ID", "상위 항목ID", "서비스", "세대"] + fields + ["값 정의", "설명"]
    rows = [[it.get(c, "") for c in cols[:5 + len(fields)]] + ["\n".join(vals[it["항목ID"]]), "\n\n".join(descs[it["항목ID"]])]
            for it in raw.items]
    _table(wb.create_sheet("항목상세"), cols, rows, {"시트": 22, "항목ID": 22, "상위 항목ID": 18, "이름": 40, "적용 판단 기준": 40,
                                                   "Tool 표시": 26, "비고": 26, "Remark": 26, "값 정의": 34, "설명": 60}, "C2")

    # 차종
    n_sheets = defaultdict(int)
    for m in raw.membership:
        n_sheets[m["차종코드"]] += 1
    _table(wb.create_sheet("차종"), ["차종코드", "원본 표기", "담당자", "속한 시트 수"],
           [[p["차종코드"], p.get("원본 표기", ""), p.get("담당자", ""), n_sheets[p["차종코드"]]] for p in raw.projects],
           {"원본 표기": 50}, "B2")

    # 개정이력
    hcols = ["Rev", "날짜", "작성자", "Function Set", "종류", "시트", "내용", "단계", "차종", "기준(블록도·기능사양표·SCR)", "메모"]
    _table(wb.create_sheet("개정이력"), hcols, [[h.get(c, "") for c in hcols] for h in raw.history],
           {"내용": 70, "메모": 40, "기준(블록도·기능사양표·SCR)": 30}, "B2")

    # 참고문서
    for doc in dict.fromkeys(d["문서"] for d in raw.refdocs):
        wr = wb.create_sheet(doc[:31])
        for d in raw.refdocs:
            if d["문서"] == doc:
                cell = wr.cell(int(d["행"]), int(d["열"]))
                _text(cell, d["내용"])
                cell.alignment = WRAP
        for j in range(1, 12):
            wr.column_dimensions[get_column_letter(j)].width = 22

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
