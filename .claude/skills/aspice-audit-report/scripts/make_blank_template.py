#!/usr/bin/env python3
"""사람 완성본 → 빈 양식. 답 칸만 비우고 문항·구조·드롭다운은 보존한다.

usage: python make_blank_template.py <완성본.xlsx> <빈양식.xlsx>
"""
import sys
import openpyxl
from openpyxl.cell.cell import MergedCell
import config


def main(src, out):
    wb = openpyxl.load_workbook(src)  # 서식/드롭다운 보존 (data_only 금지)
    sheets = config.find_sheets(wb)
    cleared = 0
    for key, cols in config.CLEAR_COLS.items():
        name = sheets.get(key)
        if not name:
            continue
        ws = wb[name]
        for row in range(config.DATA_START_ROW, ws.max_row + 1):
            for c in cols:
                cell = ws.cell(row=row, column=c)
                if isinstance(cell, MergedCell):
                    continue
                if cell.value is not None:
                    cell.value = None
                    cleared += 1
    wb.save(out)
    print(f"빈 양식 저장: {out} (비운 답 칸 {cleared}개)")
    # 컬럼 검증용 한 행 출력
    pn = sheets.get("process")
    if pn:
        ws = wb[pn]
        r = config.DATA_START_ROW
        q = ws.cell(r, config.PROCESS_COLS["question"]).value
        print(f"  [검증] Process {r}행 문항 칸 = {str(q)[:50]!r} (문항이 보존돼야 정상)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
