#!/usr/bin/env python3
"""AI가 작성한 사람급 코멘트(comments.json)를 결과 체크리스트에 주입한다.

comments.json 형식:
[ {"sheet":"wp","product":"프로젝트 계획서","no":2,
   "comment":"260624 (AI·본문정독): ...","result":"Pass"}, ... ]
- sheet : "wp" 또는 "process"
- product: WP의 No는 산출물 간 중복되므로 product 부분문자열로 행을 구분(필수 권장)
- no : 해당 시트의 No 열 값
- result: 선택(Pass/Fail/Conditional pass). 생략 시 Result는 건드리지 않음.

usage: python write_comments.py <결과.xlsx> <comments.json>
"""
import sys
import json
import openpyxl
import config


def main(result, cj):
    items = json.load(open(cj, encoding="utf-8"))
    wb = openpyxl.load_workbook(result)
    sh = config.find_sheets(wb)
    colmap = {"wp": config.WP_COLS, "process": config.PROCESS_COLS}
    n = 0
    missed = []
    for it in items:
        key = it["sheet"]
        ws = wb[sh[key]]
        C = colmap[key]
        prod = it.get("product")
        pcol = C.get("product")
        hit = False
        for row in range(config.DATA_START_ROW, ws.max_row + 1):
            if ws.cell(row, 1).value != it["no"]:
                continue
            if prod and pcol and prod not in str(ws.cell(row, pcol).value or ""):
                continue
            ws.cell(row, C["comments"]).value = it["comment"]
            if it.get("result"):
                ws.cell(row, C["result"]).value = it["result"]
                ws.cell(row, C["applicable"]).value = "Yes"
            n += 1
            hit = True
        if not hit:
            missed.append((it.get("product"), it["no"]))
    wb.save(result)
    print(f"주입된 셀: {n} | 미주입: {len(missed)}")
    for m in missed:
        print("  miss", m)
    return missed


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
