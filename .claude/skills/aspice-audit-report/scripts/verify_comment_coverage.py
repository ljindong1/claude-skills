#!/usr/bin/env python3
"""사람급 코멘트 전수 커버리지 최종 확인 (WP + Process 모두).

목적: 리포트의 WP/Process 점검대상(Applicable=Yes) 항목이 '하나도 빠짐없이'
사람급(AI 심층) 코멘트를 가졌는지 검사하고, 빠진/얕은(1차 템플릿) 항목을
시트·산출물별로 보고한다. 사람 작성본이 있으면 사람이 코멘트한 항목 기준으로도 대조.

usage:
  python verify_comment_coverage.py <결과.xlsx> [사람작성본.xlsx]

종료코드: 미달(빠짐 또는 비심층)이 있으면 1, 전부 충족이면 0.
'심층' 판정은 코멘트에 AI 정독 마커(DEEP_MARKERS)가 있는지로 본다.
"""
import sys
import openpyxl
import config
from collections import defaultdict

DEEP_MARKERS = ["AI·본문", "AI·결과서", "AI·검토", "AI·정독", "AI·구조", "AI·추적",
                "AI·데이터", "AI·확인", "본문+검토", "본문정독", "검토결과서"]

SHEETS = [("wp", config.WP_COLS, "product"),
          ("process", config.PROCESS_COLS, "output_product")]


def is_deep(c):
    return bool(c) and any(m in str(c) for m in DEEP_MARKERS)


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
            cur = str(g).strip().splitlines()[0][:24]
        if no is None:
            continue
        yield no, cur, str(ws.cell(r, C["applicable"]).value or "").strip(), ws.cell(r, C["comments"]).value


def main(result, human=None):
    wb = openpyxl.load_workbook(result, data_only=True)
    ok = True
    grand = [0, 0]
    human_gap = []
    hwb = openpyxl.load_workbook(human, data_only=True) if human else None

    for key, C, gcol in SHEETS:
        ws = find(wb, key)
        if ws is None:
            continue
        by = defaultdict(lambda: {"t": 0, "deep": 0, "shallow": [], "miss": []})
        for no, g, ap, cmt in rows(ws, C, gcol):
            if ap != "Yes":
                continue
            d = by[g]
            d["t"] += 1
            if not (cmt and str(cmt).strip()):
                d["miss"].append(no)
            elif is_deep(cmt):
                d["deep"] += 1
            else:
                d["shallow"].append(no)
        st = sum(v["t"] for v in by.values())
        sd = sum(v["deep"] for v in by.values())
        grand[0] += st; grand[1] += sd
        print(f"\n=== [{key.upper()}] 점검대상 {st} / 심층 {sd} ({(sd/st*100 if st else 0):.1f}%) ===")
        print(f"{'산출물/그룹':30s} 대상  심층  비심층  빠짐")
        for g in by:
            d = by[g]; bad = len(d["shallow"]) + len(d["miss"])
            if bad:
                ok = False
            print(f"{str(g)[:28]:30s} {d['t']:4d} {d['deep']:5d} {len(d['shallow']):6d} {len(d['miss']):5d}" + ("  ◀" if bad else ""))
            if d["miss"]:
                print(f"      빠짐 No: {d['miss']}")
            if d["shallow"]:
                print(f"      비심층 No: {d['shallow']}")

        if hwb is not None:
            hws = find(hwb, key)
            if hws is not None:
                ai = {no: c for no, _, _, c in rows(ws, C, gcol)}
                aip = {}
                for no, g, ap, c in rows(ws, C, gcol):
                    aip[(g, no)] = c
                for no, g, ap, cmt in rows(hws, C, gcol):
                    if ap == "Yes" and cmt and str(cmt).strip():
                        # WP는 (product,no), Process는 no 유일이라 no로
                        v = aip.get((g, no)) if key == "wp" else ai.get(no)
                        if not is_deep(v):
                            human_gap.append((key, g, no))

    print(f"\n>>> 전체 점검대상 {grand[0]} / 심층 {grand[1]} ({(grand[1]/grand[0]*100 if grand[0] else 0):.1f}%)")
    if human:
        print(f">>> 사람 코멘트 대비 AI 비심층/빠짐: {len(human_gap)}건")
        for x in human_gap[:60]:
            print("   ", x)

    if ok and not human_gap:
        print("\n[PASS] WP·Process 점검대상 전 항목이 사람급(심층) 코멘트를 보유함.")
        return 0
    print("\n[FAIL] 보완 필요 — 위 '빠짐/비심층' 항목의 본문·검토결과서를 정독해 코멘트 작성 후 재주입하라.")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
