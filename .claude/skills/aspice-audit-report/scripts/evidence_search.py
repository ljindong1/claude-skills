#!/usr/bin/env python3
"""대체 근거(compensating evidence) 폴더 탐색기 — Phase C.

[evidence 브리핑 재정의, references/roadmap.md]
Pass 기준은 "지정 산출물의 특정 위치"가 아니라 "Intent를 충족하는 명확한 evidence가
실제로 정독한 산출물에 명시적으로 존재하는가"다. 1차 표준 위치에 없을 때, 프로젝트
특성상 대체된 근거(별도 파일·회의록·다른 활동)를 폴더 전체에서 찾도록 돕는다.

이 스크립트는 판정하지 않는다. summarize_folder.py가 만든 folder_digest.md
(파일별 시트명·헤딩·첫 행·검출 ID·버전을 한 장으로 모은 것)에서 키워드를 검색해
'어느 파일의 어디를 열어보면 되는지' 후보를 제시한다. 최종 확인은 AI가 그 파일
본문을 정독해서 한다.

usage:
  # intent_map의 특정 문항에 대한 대체 근거 후보
  python evidence_search.py folder_digest.md --intent intent_map.json --sheet wp --no 2 --product "프로젝트 계획서"
  # 임의 키워드로 검색
  python evidence_search.py folder_digest.md --kw 위험관리 --kw 리스크 --kw 회의록
"""
import argparse
import re
import sys

import intent_lib


def load_digest(path):
    """folder_digest.md 를 (현재 파일명, 라인) 스트림으로 파싱.

    다이제스트는 파일별 섹션으로 구성된다고 가정하고, 헤딩(## 또는 # 로 시작,
    혹은 파일 확장자를 포함한 줄)을 '현재 파일' 경계로 삼는다.
    """
    lines = []
    cur = "(파일 미상)"
    file_re = re.compile(r"\.(docx|xlsx|xls|pdf|md|zip|csv)\b", re.IGNORECASE)
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.lstrip("#").strip()
            if (line.startswith("#") or line.startswith("##")) and file_re.search(line):
                cur = stripped
            elif file_re.search(line) and len(line) < 200 and line.strip().endswith(
                    (".docx", ".xlsx", ".xls", ".pdf", ".md", ".csv")):
                cur = stripped
            lines.append((cur, line))
    return lines


def search(lines, keywords):
    """키워드(부분 문자열, 대소문자 무시)별로 매칭 라인을 모은다."""
    hits = {}
    lowered = [(f, ln, ln.lower()) for f, ln in lines]
    for kw in keywords:
        k = str(kw).strip()
        if not k:
            continue
        kl = k.lower()
        found = [(f, ln) for f, ln, low in lowered if kl in low]
        if found:
            hits[k] = found
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("digest", help="summarize_folder.py 가 만든 folder_digest.md")
    ap.add_argument("--kw", action="append", default=[], help="검색 키워드(여러 번)")
    ap.add_argument("--intent", default=None, help="intent_map.json (문항의 대체근거 키워드 사용)")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--no", type=int, default=None)
    ap.add_argument("--product", default=None)
    a = ap.parse_args()

    keywords = list(a.kw)
    if a.intent and a.sheet is not None and a.no is not None:
        im = intent_lib.IntentMap.load(a.intent)
        phrases = im.alt_keywords(a.sheet, a.no, a.product)
        # 긴 문구는 그대로 + 의미있는 토큰(2자 이상, 조사성 접미 제거)까지 검색해 recall 향상
        toks = []
        for ph in phrases:
            for w in re.split(r"[\s/·,()]+", str(ph)):
                w = w.strip("의를을이가은는과와")
                if len(w) >= 2:
                    toks.append(w)
        keywords += phrases + toks
        line = im.intent_line(a.sheet, a.no, a.product)
        print(line)
    # 중복 제거(순서 보존)
    seen = set(); keywords = [k for k in keywords if not (k in seen or seen.add(k))]
    if not keywords:
        print("검색할 키워드가 없습니다 (--kw 또는 --intent+--sheet+--no).")
        return 2

    lines = load_digest(a.digest)
    hits = search(lines, keywords)
    if not hits:
        print("\n대체 근거 후보 없음 — 폴더 다이제스트에서 키워드가 확인되지 않음.")
        print("→ Not-Pass 시 '확인 필요 — 해당 활동 수행 근거가 폴더에서 식별되지 않음'으로 남긴다.")
        return 1

    print("\n=== 대체 근거 후보 (파일 · 근거 라인) — 최종 확인은 본문 정독 ===")
    for kw, found in hits.items():
        print(f"\n[{kw}] {len(found)}건")
        seen = set()
        for f, ln in found[:12]:
            key = (f, ln.strip()[:80])
            if key in seen:
                continue
            seen.add(key)
            print(f"  · {f}\n      {ln.strip()[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
