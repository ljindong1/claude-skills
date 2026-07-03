#!/usr/bin/env python3
"""사람 작성본 vs AI 리포트 코멘트 비교표(검증 산출물) — WP + Process 분리 시트.

최종 확인 단계에서 사람 코멘트(좌)와 AI 코멘트(우)를 항목별로 나란히 두어
사람급 도달 여부를 사람이 눈으로 대조하게 한다.

★ 검증용 임시 산출물이다. 파일명에 _검증용을 붙여 최종 납품물(체크리스트)과 구분하고
   검증이 끝나면 삭제해도 된다.

시트(리포트와 동일하게 WP/Process를 나눠 본다):
  - 요약: 시트(WP/Process)·산출물별 (사람 Yes 코멘트 / AI / 심층 / 비고)
  - 상세 비교(WP): No · 산출물 · 점검 항목 · 사람 · AI
  - 상세 비교(Process): No · 활동(출력 산출물) · 점검 항목 · 사람 · AI

usage:
  python build_comparison.py <결과.xlsx> <사람작성본.xlsx> <출력.xlsx>
"""
import sys
import openpyxl
import config
from collections import defaultdict
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

DEEP = ["AI·본문", "AI·결과서", "AI·검토", "AI·정독", "AI·구조", "AI·추적",
        "AI·데이터", "AI·확인", "본문+검토", "본문정독", "검토결과서"]

# (요약 라벨, prefix, 컬럼맵, 그룹컬럼, 상세시트명)
SHEETS = [("WP", "wp", config.WP_COLS, "product", "상세 비교(WP)"),
          ("Process", "process", config.PROCESS_COLS, "output_product", "상세 비교(Process)")]


def is_deep(c):
    return bool(c) and any(m in str(c) for m in DEEP)


def find(wb, prefix):
    for sn in wb.sheetnames:
        if sn.startswith(config.SHEET_PREFIX[prefix]):
            return wb[sn]
    return None


def rows(ws, C, gcol):
    cur = None
    for r in range(config.DATA_START_ROW, ws.max_row + 1):
        no = ws.cell(r, 1).value
        g = ws.cell(r, C[gcol]).value
        if g and str(g).strip():
            cur = str(g).strip().splitlines()[0][:28]
        if no is None:
            continue
        yield (no, cur,
               ws.cell(r, C["question"]).value,
               str(ws.cell(r, C["applicable"]).value or "").strip(),
               ws.cell(r, C["comments"]).value)


def style_header(rowcells, hdr, fill, bd):
    for c in rowcells:
        c.font = hdr; c.fill = fill
        c.alignment = Alignment(horizontal="center"); c.border = bd


def main(result, human, out):
    awb = openpyxl.load_workbook(result, data_only=True)
    hwb = openpyxl.load_workbook(human, data_only=True)

    hdr = Font(bold=True, color="FFFFFF"); fill = PatternFill("solid", fgColor="305496")
    thin = Side(style="thin", color="BBBBBB"); bd = Border(thin, thin, thin, thin)

    owb = openpyxl.Workbook()
    summ = owb.active; summ.title = "요약"
    summ.append(["시트", "산출물/활동", "사람 코멘트(Yes)", "AI 코멘트", "AI 사람급(심층)", "비고"])
    style_header(summ[1], hdr, fill, bd)

    for label, key, C, gcol, detail_name in SHEETS:
        aws = find(awb, key); hws = find(hwb, key)
        if aws is None or hws is None:
            continue
        ai_pk = {}; ai_no = {}
        for no, g, q, ap, c in rows(aws, C, gcol):
            ai_pk[(g, no)] = c; ai_no[no] = c

        ps = defaultdict(lambda: [0, 0, 0]); order = []; detail = []
        for no, g, q, ap, hc in rows(hws, C, gcol):
            if ap != "Yes" or not (hc and str(hc).strip()):
                continue
            if g not in ps:
                order.append(g)
            ac = ai_pk.get((g, no)) if key == "wp" else ai_no.get(no)
            ps[g][0] += 1
            if ac and str(ac).strip():
                ps[g][1] += 1
                if is_deep(ac):
                    ps[g][2] += 1
            detail.append((no, g, q, hc, ac))

        for g in order:
            a, b, c = ps[g]
            summ.append([label, g, a, b, c, "사람급 달성" if c == a else "보완 필요"])

        ds = owb.create_sheet(detail_name)
        col2 = "산출물" if key == "wp" else "활동(출력 산출물)"
        ds.append(["No", col2, "점검 항목", "사람 Review Comments", "AI Review Comments"])
        style_header(ds[1], hdr, fill, bd)
        detail.sort(key=lambda x: (order.index(x[1]) if x[1] in order else 999, x[0]))
        for no, g, q, hc, ac in detail:
            ds.append([no, g, str(q or "").strip(), str(hc).strip(), str(ac or "").strip()])
        for row in ds.iter_rows(min_row=2):
            for c in row:
                c.border = bd; c.alignment = Alignment(vertical="top", wrap_text=True)
        ds.column_dimensions["A"].width = 6; ds.column_dimensions["B"].width = 24
        ds.column_dimensions["C"].width = 32; ds.column_dimensions["D"].width = 60
        ds.column_dimensions["E"].width = 60
        ds.freeze_panes = "A2"

    for row in summ.iter_rows(min_row=2):
        for c in row:
            c.border = bd; c.alignment = Alignment(vertical="center", wrap_text=True)
    summ.column_dimensions["A"].width = 9; summ.column_dimensions["B"].width = 26
    for col in "CDE":
        summ.column_dimensions[col].width = 13
    summ.column_dimensions["F"].width = 16
    summ.freeze_panes = "A2"

    owb.save(out)
    print(f"비교표 저장: {out}  (시트: {[s.title for s in owb.worksheets]})")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
