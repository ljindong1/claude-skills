#!/usr/bin/env python3
"""빈 양식에 산출물 매핑 + 1차 자동 판정을 채운다.

usage: python fill_checklist.py <빈양식.xlsx> <결과.xlsx> --map deliverable_map.json
"""
import re
import json
import argparse
import datetime
import openpyxl
import config
import classification_rules as rules


def norm(s):
    return re.sub(r"[\s()◆\[\]]", "", str(s or "")).lower()


def load_map(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_ev(pn, evidence):
    # 가장 구체적인(긴) 키가 이긴다 — 일반 키('회의록')가 특정 키('검토회의록')를 가로채는 것 방지
    best, best_len = None, -1
    for kw, val in evidence.items():
        nk = norm(kw)
        if nk and nk in pn and len(nk) > best_len:
            best, best_len = val, len(nk)
    if best:
        return best[0], (best[1] if len(best) > 1 else "")
    return None


def is_na(product, extra):
    if rules.is_design_phase_target(product):   # 계획서·정적검증은 미대상에서 제외(점검대상 유지)
        return False
    if rules.is_na_product(product):
        return True
    pn = norm(product)
    return any(norm(x) in pn for x in extra)


def fill(blank, out, mapping):
    today = datetime.date.today().strftime("%y%m%d")
    ev = mapping.get("evidence", {})
    na_reason = mapping.get("na_default_reason", "단계 미도래/해당없음 점검 범위")
    na_extra = mapping.get("na_products", [])
    wb = openpyxl.load_workbook(blank)
    sh = config.find_sheets(wb)
    counts = dict(target=0, wp_no=0, wp_pass=0, wp_chk=0, wp_unk=0, pc_no=0, pc_chk=0)

    # Target
    T = config.TARGET_COLS
    ws = wb[sh["target"]]
    for row in range(config.DATA_START_ROW, ws.max_row + 1):
        prod = ws.cell(row, T["product"]).value
        if not prod:
            continue
        hit = find_ev(norm(prod), ev)
        if hit:
            ws.cell(row, T["file"]).value = hit[0]
            ws.cell(row, T["bigo"]).value = "[점검 대상]"
        elif is_na(prod, na_extra):
            ws.cell(row, T["bigo"]).value = "[점검 미대상] " + na_reason
        else:
            ws.cell(row, T["bigo"]).value = "[점검 대상] 확인 필요 - 자동 식별 안됨"
        counts["target"] += 1

    # WP
    W = config.WP_COLS
    ws = wb[sh["wp"]]
    for row in range(config.DATA_START_ROW, ws.max_row + 1):
        no = ws.cell(row, 1).value
        ques = ws.cell(row, W["question"]).value
        if no is None or not ques:
            continue
        prod = ws.cell(row, W["product"]).value
        hit = find_ev(norm(prod), ev)
        if hit:
            ws.cell(row, W["applicable"]).value = "Yes"
            evstr = (hit[0] + " (" + hit[1] + ")") if hit[1] else hit[0]
            res, com = rules.judge(ques, evstr)
            com = com.replace("(AI 1차)", today + " (AI 1차)")
            if res:
                ws.cell(row, W["result"]).value = res
                counts["wp_pass"] += 1
            else:
                counts["wp_chk"] += 1
            ws.cell(row, W["comments"]).value = com
        elif is_na(prod, na_extra):
            ws.cell(row, W["applicable"]).value = "No"
            ws.cell(row, W["comments"]).value = "[점검 미대상] " + na_reason
            counts["wp_no"] += 1
        else:
            # 매핑된 파일이 없어도 미대상이 아니면 점검대상이다 → Applicable=Yes, 판정은 보류(확인 필요)
            ws.cell(row, W["applicable"]).value = "Yes"
            ws.cell(row, W["comments"]).value = today + " (AI 1차): 대상 산출물 자동 식별 안됨 - 확인 필요(폴더 외/codebeamer 가능)"
            counts["wp_unk"] += 1

    # Process — Yes/No 스코핑: 실행시점 후행단계/미대상 → No, 출력 산출물 식별 → Yes, 미식별 → 비움(확인 필요)
    P = config.PROCESS_COLS
    ws = wb[sh["process"]]
    for row in range(config.DATA_START_ROW, ws.max_row + 1):
        ques = ws.cell(row, P["question"]).value
        if not ques:
            continue
        out_p = ws.cell(row, P["output_product"]).value
        timing = ws.cell(row, P["timing"]).value
        if rules.is_later_phase_timing(timing):
            t18 = str(timing or "")[:18]
            ws.cell(row, P["applicable"]).value = "No"
            ws.cell(row, P["comments"]).value = "[점검 미대상] 실행시점 후행단계(" + t18 + ") - 단계 미도래"
            counts["pc_no"] += 1
        elif is_na(out_p, na_extra):
            ws.cell(row, P["applicable"]).value = "No"
            ws.cell(row, P["comments"]).value = "[점검 미대상] " + na_reason
            counts["pc_no"] += 1
        else:
            ws.cell(row, P["applicable"]).value = "Yes"
            tail = "출력 산출물 식별됨. " if find_ev(norm(out_p), ev) else ""
            ws.cell(row, P["comments"]).value = today + " (AI 1차): " + tail + "절차 수행 근거(PMS 승인/시스템 기록)는 직접 확인 필요"
            counts["pc_chk"] += 1

    add_notice(wb, counts, today)
    wb.save(out)
    issues = integrity(wb, sh)
    print("저장:", out)
    print("집계:", counts)
    print("정합성 이슈:", len(issues))
    for i in issues[:10]:
        print("  ", i)


def integrity(wb, sh):
    issues = []
    W = config.WP_COLS
    ws = wb[sh["wp"]]
    for row in range(config.DATA_START_ROW, ws.max_row + 1):
        no = ws.cell(row, 1).value
        ques = ws.cell(row, W["question"]).value
        if no is None or not ques:
            continue
        ap = ws.cell(row, W["applicable"]).value
        rs = ws.cell(row, W["result"]).value
        cm = ws.cell(row, W["comments"]).value
        if ap == "No" and rs:
            issues.append(("WP", row, "No인데 Result 존재"))
        if not cm:
            issues.append(("WP", row, "코멘트 없음"))
    return issues


def add_notice(wb, counts, today):
    from openpyxl.styles import Font, PatternFill, Alignment
    name = "AI점검_안내"
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name, 1)
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 92
    ws.sheet_view.showGridLines = False
    chk = counts["wp_chk"] + counts["wp_unk"]
    lines = [
        ("AI 1차 자동 점검 결과 — 안내", True, 14, "1F3864", "FFFFFF"),
        (today + " · 본 결과는 AI 1차 자동 점검이며 최종 판정은 사람이 검증해야 함", True, 10, "000000", "FFF2CC"),
        ("· Pass = 문서에 해당 절·항목이 존재함(형식·존재성) 수준이며 내용 적정성은 미검증", False, 10, "000000", None),
        ("· 승인·배포·추적성·일관성 등은 자동 Pass 금지 → 확인 필요로 보류", False, 10, "000000", None),
        ("· 사내 시스템 URL은 접근 불가 → 확인 필요", False, 10, "000000", None),
        ("· Process Yes/No는 출력 산출물 식별·실행시점 기반 1차 스코핑 (사람 확정 필요)", False, 10, "000000", None),
        ("· 요약 WP: Pass " + str(counts["wp_pass"]) + " / 미대상 " + str(counts["wp_no"]) + " / 확인필요 " + str(chk), False, 10, "000000", None),
        ("· 요약 Process: 미대상 " + str(counts["pc_no"]) + " / 확인필요·식별 " + str(counts["pc_chk"]), False, 10, "000000", None),
    ]
    for i, (t, b, sz, col, fill) in enumerate(lines, start=2):
        c = ws.cell(i, 2, t)
        c.font = Font(name="맑은 고딕", bold=b, size=sz, color=col)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        ws.row_dimensions[i].height = 20


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("blank")
    ap.add_argument("out")
    ap.add_argument("--map", required=True)
    a = ap.parse_args()
    fill(a.blank, a.out, load_map(a.map))
