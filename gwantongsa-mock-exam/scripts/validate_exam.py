#!/usr/bin/env python3
"""관통사 모의고사 JSON 검증 스크립트.

사용법:
    python3 validate_exam.py exam.json [--history history.txt]

검사 항목:
  [구조]   과목 2개(국사 1~25번, 관광자원해설 26~50번), 문항당 4지선다, 정답 1~4
  [분포]   과목별 정답 번호 분포(각 번호 4~9회), 같은 번호 3연속 초과 금지
  [국사]   시대 배분(선사 1~2, 근현대 2~4), 배열형 5~8문항
  [해설]   해설 40자 이상, 키워드 1개 이상
  [중복]   이력 파일과 키워드 대조 (경고로 보고 — 경고 문항은 반드시 주제 교체 검토)

종료 코드: 0 = 통과(경고 없을 수도, 있을 수도), 1 = 구조/규칙 위반(FAIL).
출력 마지막 줄이 RESULT: PASS / RESULT: FAIL 이다.
경고(WARN)가 있으면 통과여도 해당 문항을 반드시 검토하라.
"""
import json
import sys
import argparse

ERAS = {"선사", "고대", "고려", "조선", "근현대", "통합"}
CIRCLED = "①②③④"

fails = []
warns = []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def check_structure(exam):
    subjects = exam.get("subjects", [])
    names = [s.get("name") for s in subjects]
    if names != ["국사", "관광자원해설"]:
        fail(f"과목 구성이 [국사, 관광자원해설]이 아님: {names}")
        return
    expected_no = 1
    for s in subjects:
        qs = s.get("questions", [])
        if len(qs) != 25:
            fail(f"{s['name']}: 문항 수 {len(qs)}개 (25개여야 함)")
        for q in qs:
            no = q.get("no")
            if no != expected_no:
                fail(f"{s['name']}: 문항 번호 불연속 (기대 {expected_no}, 실제 {no})")
            expected_no = (no or expected_no) + 1
            _check_question(s["name"], q)


def _check_question(subj, q):
    no = q.get("no", "?")
    tag = f"{subj} {no}번"
    choices = q.get("choices", [])
    if len(choices) != 4:
        fail(f"{tag}: 선택지 {len(choices)}개 (4개여야 함)")
    if len(set(c.strip() for c in choices)) != len(choices):
        fail(f"{tag}: 선택지에 중복 있음")
    for i, c in enumerate(choices):
        if not c or not c.strip():
            fail(f"{tag}: 선택지 {i+1}이 비어 있음")
        if c.strip()[0] in CIRCLED or (c.strip()[0].isdigit() and c.strip()[1:2] in ".)"):
            warn(f"{tag}: 선택지 텍스트에 번호 기호가 포함된 듯함 (템플릿이 자동으로 붙이므로 제거) → '{c[:20]}'")
    ans = q.get("answer")
    if not isinstance(ans, int) or not 1 <= ans <= 4:
        fail(f"{tag}: answer가 1~4 정수가 아님: {ans!r}")
    if not q.get("question", "").strip():
        fail(f"{tag}: 발문이 비어 있음")
    expl = q.get("explanation", "")
    if len(expl.strip()) < 40:
        fail(f"{tag}: 해설이 40자 미만 ({len(expl.strip())}자) — 상세 해설 필수")
    if not q.get("keywords"):
        fail(f"{tag}: keywords가 비어 있음 (중복 방지 이력에 필요)")
    if subj == "국사":
        if q.get("era") not in ERAS:
            fail(f"{tag}: era가 {sorted(ERAS)} 중 하나가 아님: {q.get('era')!r}")
        if q.get("qtype") not in {"복합", "배열", "사료", "기출변형"}:
            fail(f"{tag}: qtype이 복합/배열/사료/기출변형 중 하나가 아님: {q.get('qtype')!r}")
    else:
        if not q.get("category", "").strip():
            fail(f"{tag}: category가 비어 있음")


def check_answer_distribution(exam):
    for s in exam.get("subjects", []):
        qs = s.get("questions", [])
        answers = [q.get("answer") for q in qs if isinstance(q.get("answer"), int)]
        counts = {n: answers.count(n) for n in (1, 2, 3, 4)}
        for n, c in counts.items():
            if not 4 <= c <= 9:
                fail(f"{s['name']}: 정답 {CIRCLED[n-1]} 번이 {c}회 (4~9회 범위 밖) — 정답 번호를 재배치하라. 분포={counts}")
        run = 1
        for a, b in zip(answers, answers[1:]):
            run = run + 1 if a == b else 1
            if run > 3:
                fail(f"{s['name']}: 같은 정답 번호가 4연속 이상 등장 — 재배치하라")
                break


def check_history_composition(exam):
    kuksa = next((s for s in exam.get("subjects", []) if s.get("name") == "국사"), None)
    if not kuksa:
        return
    qs = kuksa.get("questions", [])
    era_count = {}
    for q in qs:
        era_count[q.get("era")] = era_count.get(q.get("era"), 0) + 1
    seonsa = era_count.get("선사", 0)
    modern = era_count.get("근현대", 0)
    baeyeol = sum(1 for q in qs if q.get("qtype") == "배열")
    if not 1 <= seonsa <= 2:
        fail(f"국사: 선사시대 {seonsa}문항 (1~2문항이어야 함)")
    if not 2 <= modern <= 4:
        fail(f"국사: 근현대사 {modern}문항 (2~4문항이어야 함, 4문항 초과 절대 금지)")
    if not 5 <= baeyeol <= 8:
        fail(f"국사: 시대순 배열형 {baeyeol}문항 (취약 유형 보강을 위해 5~8문항 필요)")
    print(f"  국사 시대 분포: {era_count}")
    print(f"  국사 배열형: {baeyeol}문항")


def check_duplicates(exam, history_path):
    """이력 파일 형식: 한 줄에 '날짜\t과목\t키워드1,키워드2,...'"""
    try:
        with open(history_path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and "\t" in l]
    except FileNotFoundError:
        print(f"  이력 파일 없음({history_path}) — 중복 검사 생략")
        return
    hist = []
    for l in lines:
        parts = l.split("\t")
        if len(parts) >= 3:
            hist.append((parts[0], parts[1], set(k.strip() for k in parts[2].split(",") if k.strip())))
    for s in exam.get("subjects", []):
        for q in s.get("questions", []):
            kws = set(k.strip() for k in q.get("keywords", []))
            if not kws:
                continue
            for date, subj, hkws in hist:
                if subj != s["name"]:
                    continue
                overlap = kws & hkws
                first_kw = q.get("keywords", [""])[0].strip()
                if first_kw and first_kw in hkws:
                    warn(f"{s['name']} {q.get('no')}번: 핵심 주제 '{first_kw}'가 {date} 출제 이력과 겹침 — 주제를 교체하라")
                elif len(overlap) >= 2:
                    warn(f"{s['name']} {q.get('no')}번: {date} 이력과 키워드 {len(overlap)}개 겹침({', '.join(sorted(overlap))}) — 같은 문제의 재탕이 아닌지 확인하라")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam_json")
    ap.add_argument("--history", default=None)
    args = ap.parse_args()

    with open(args.exam_json, encoding="utf-8") as f:
        exam = json.load(f)

    print("== 구조 검사 ==")
    check_structure(exam)
    print("== 정답 분포 검사 ==")
    check_answer_distribution(exam)
    print("== 국사 구성 검사 ==")
    check_history_composition(exam)
    if args.history:
        print("== 중복(이력) 검사 ==")
        check_duplicates(exam, args.history)

    print()
    for w in warns:
        print(f"WARN: {w}")
    for e in fails:
        print(f"FAIL: {e}")
    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}건 위반, 경고 {len(warns)}건)")
        sys.exit(1)
    print(f"RESULT: PASS (경고 {len(warns)}건)")
    sys.exit(0)


if __name__ == "__main__":
    main()
