#!/usr/bin/env python3
"""AI 작성본 vs 사람 작성본 행 단위 비교 → 검증표(요약 + 불일치 상세).

usage: python verify_against_baseline.py <AI작성본.xlsx> <사람작성본.xlsx> <검증표.xlsx>
두 파일은 같은 양식이어야 한다(행 1:1 비교).
"""
import sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import config


def n(v):
    return "" if v is None else str(v).strip()


def collect(H, A, sheet, qcol, labcol, acol, rcol):
    h, a = H[sheet], A[sheet]
    out = []
    for r in range(config.DATA_START_ROW, h.max_row + 1):
        q = h.cell(r, qcol).value
        if not q:
            continue
        out.append((r, n(h.cell(r, labcol).value), n(q),
                    n(h.cell(r, acol).value), n(h.cell(r, rcol).value),
                    n(a.cell(r, acol).value), n(a.cell(r, rcol).value)))
    return out


def classify(ha, hr, aa, ar):
    hy, ay = ha == "Yes", aa == "Yes"
    if hy and ay:
        if not ar:
            return "미판정"
        if hr == "Fail" and ar in ("Pass", "Conditional pass"):
            return "위험오판"
        if (hr == ar) or (hr in ("Pass", "Conditional pass") and ar == "Pass"):
            return "일치"
        return "결과불일치"
    if ay and not hy:
        return "과대"
    if hy and not ay:
        return "과소"
    return "일치"


def metrics(rows):
    m = dict(tot=len(rows), scope=0, under=0, over=0, rden=0, rmatch=0, rmiss=0, fp=0)
    for r, lab, q, ha, hr, aa, ar in rows:
        hy, ay = ha == "Yes", aa == "Yes"
        if ha == aa:
            m["scope"] += 1
        elif hy and not ay:
            m["under"] += 1
        elif ay and not hy:
            m["over"] += 1
        if hy and hr:
            m["rden"] += 1
            if ay and not ar:
                m["rmiss"] += 1
            elif ay and hr == "Fail" and ar in ("Pass", "Conditional pass"):
                m["fp"] += 1
            elif ay and ((hr == ar) or (hr in ("Pass", "Conditional pass") and ar == "Pass")):
                m["rmatch"] += 1
            elif not ay:
                m["rmiss"] += 1
    return m


def main(ai, human, out):
    A = openpyxl.load_workbook(ai, data_only=True)
    H = openpyxl.load_workbook(human, data_only=True)
    sh = config.find_sheets(H)
    P, W = config.PROCESS_COLS, config.WP_COLS
    wp = collect(H, A, sh["wp"], W["question"], W["product"], W["applicable"], W["result"])
    pc = collect(H, A, sh["process"], P["question"], P["output_product"], P["applicable"], P["result"])
    det = []
    for sheet, rows in (("WP", wp), ("Process", pc)):
        for r, lab, q, ha, hr, aa, ar in rows:
            cat = classify(ha, hr, aa, ar)
            if cat in ("과소", "과대", "위험오판", "결과불일치"):
                det.append((cat, sheet, r, lab, q[:60],
                            f"{ha or '-'}/{hr or '-'}", f"{aa or '-'}/{ar or '-'}"))
    order = {"위험오판": 0, "과소": 1, "결과불일치": 2, "과대": 3}
    det.sort(key=lambda x: (order[x[0]], x[1], x[2]))
    mwp, mpc = metrics(wp), metrics(pc)

    wb = openpyxl.Workbook()
    F, navy, band, warn = "맑은 고딕", "1F3864", "D9E1F2", "FCE4D6"
    thin = Side(style="thin", color="BFBFBF")
    bd = Border(thin, thin, thin, thin)

    def st(c, b=False, sz=10, col="000000", fill=None, h="left"):
        c.font = Font(name=F, bold=b, size=sz, color=col)
        c.alignment = Alignment(horizontal=h, vertical="center", wrap_text=True)
        c.border = bd
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)

    s = wb.active
    s.title = "요약"
    s.merge_cells("A1:E1"); s["A1"] = "AI 1차 자동 점검 vs 사람 작성본 — 검증 요약"
    st(s["A1"], True, 14, "FFFFFF", navy, "center")
    s["A3"] = "[ ① 스코핑(Applicable Yes/No) 정확도 ]"; st(s["A3"], True, 11, "1F3864", band); s.merge_cells("A3:E3")
    for j, x in enumerate(["시트", "전체", "일치", "AI 과소(누락)", "AI 과대"]):
        st(s.cell(4, j + 1), True, 10, "FFFFFF", navy, "center"); s.cell(4, j + 1).value = x
    for i, (nm, m) in enumerate((("WP", mwp), ("Process", mpc))):
        pct = round(m["scope"] / m["tot"] * 100) if m["tot"] else 0
        for j, v in enumerate([nm, m["tot"], f"{m['scope']} ({pct}%)", m["under"], m["over"]]):
            st(s.cell(5 + i, j + 1), False, 10, "000000", None, "center"); s.cell(5 + i, j + 1).value = v
    s["A8"] = "[ ② 결과 판정 정확도 (사람이 Pass/Fail 한 항목 기준) ]"; st(s["A8"], True, 11, "1F3864", band); s.merge_cells("A8:E8")
    for j, x in enumerate(["시트", "사람 판정 수", "AI 일치", "AI 미판정", "⚠⚠ 위험오판"]):
        st(s.cell(9, j + 1), True, 10, "FFFFFF", navy, "center"); s.cell(9, j + 1).value = x
    for i, (nm, m) in enumerate((("WP", mwp), ("Process", mpc))):
        for j, v in enumerate([nm, m["rden"], m["rmatch"], m["rmiss"], m["fp"]]):
            st(s.cell(10 + i, j + 1), False, 10, "C00000" if (j == 4 and v) else "000000", None, "center")
            s.cell(10 + i, j + 1).value = v
    for col, w in zip("ABCDE", [10, 12, 16, 16, 12]):
        s.column_dimensions[col].width = w

    d = wb.create_sheet("불일치 상세")
    d.merge_cells("A1:G1"); d["A1"] = f"불일치 상세 {len(det)}건 (위험오판→AI누락→결과상이→AI과대)"
    st(d["A1"], True, 12, "FFFFFF", navy, "center")
    for j, x in enumerate(["구분", "시트", "행", "산출물/절차", "문항", "사람 A/R", "AI A/R"]):
        st(d.cell(3, j + 1), True, 10, "FFFFFF", navy, "center"); d.cell(3, j + 1).value = x
    cmap = {"위험오판": warn, "과소": "FFF2CC", "결과불일치": "FFF2CC", "과대": "F2F2F2"}
    disp = {"위험오판": "⚠⚠ 위험오판", "과소": "⚠ AI 누락", "결과불일치": "결과 상이", "과대": "AI 과대"}
    for i, (cat, sheet, row, lab, q, hv, av) in enumerate(det):
        for j, v in enumerate([disp[cat], sheet, row, lab, q, hv, av]):
            st(d.cell(4 + i, j + 1), j == 0, 9, "000000", cmap[cat] if j == 0 else None,
               "center" if j in (1, 2, 5, 6) else "left")
            d.cell(4 + i, j + 1).value = v
    for col, w in zip("ABCDEFG", [12, 8, 6, 26, 46, 16, 16]):
        d.column_dimensions[col].width = w
    d.freeze_panes = "A4"
    wb.save(out)
    print("검증표 저장:", out)
    print("WP", mwp)
    print("Process", mpc)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:4])
