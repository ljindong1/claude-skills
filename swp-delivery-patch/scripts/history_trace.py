#!/usr/bin/env python3
"""설정 키 하나(또는 여럿)의 값을 HAE 회차별 배포본과 당사 저장소에서 회차순으로 뽑는다 — 기본 원칙 8(과거 이력).
   이번 배포본이 이전 회차 보정을 되돌린 값이면 '되돌림 의심'으로 표시한다(three-way-merge §4.8).

  python history_trace.py --file Configuration/Ecu/Ecud_EcuM.arxml --key PMem_Driver \
      --rev "3.0.18=<3.0.18 배포본 루트>" --rev "3.0.18 08-31 보정=<보정본 루트>" --rev "3.0.19=<3.0.19 배포본 루트>" \
      --ours <당사 앱 루트> [--repo <git 루트> --git-text PMem_Driver]

  --key   three_way.py 와 같은 '컨테이너 경로#파라미터' 키에서 찾을 부분 문자열 (여러 번 가능). --regex 면 정규식
  --rev   '이름=루트' 를 **회차 순서대로** 준다. 보정본·재배포본은 이름에 '보정'/'정정'/'재배포' 를 넣으면
          그 값이 마지막 회차에서 달라질 때 '되돌림 후보'로 표시한다. 루트 안에서 --file 경로를 찾고, 없으면 같은 파일 이름을 검색한다
          (보정본 zip 처럼 Ecu/ 아래에 파일만 있는 구조도 찾는다). 파일이 없는 회차는 '(파일 없음)' 으로 두고 판정에서 뺀다
  --ours  당사 앱 루트 (마지막 열)
  --git-text  당사 저장소에서 이 문자열이 들어오고 빠진 커밋(git log -S)을 함께 보여 준다
"""
import argparse, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from three_way import parse, find_in  # noqa: E402  (stdout UTF-8 설정도 three_way 가 한다)

MISSING_FILE = "(파일 없음)"
ABSENT = "(없음)"


def load(root, rel):
    p = find_in(root, rel)
    return (parse(p), p) if p else (None, None)


def fmt(v):
    if v in (MISSING_FILE, ABSENT):
        return v
    s = ", ".join(v)
    return s if len(s) <= 60 else s[:57] + "..."


def regression(seq):
    """seq: 회차순 값 목록(파일 없는 회차 제외). 마지막 값이 이전에 바뀐 적 있는 옛 값으로 돌아갔으면 설명 문자열."""
    if len(seq) < 3:
        return ""
    last_name, last = seq[-1]
    for k in range(len(seq) - 2, 0, -1):
        mid_name, mid = seq[k]
        if mid == last:
            continue
        for i in range(k - 1, -1, -1):
            old_name, old = seq[i]
            if old == last:
                return f"되돌림 의심: {old_name} 값 → {mid_name} 에서 바뀜 → {last_name} 이 다시 {old_name} 값"
        break
    return ""


def main():
    ap = argparse.ArgumentParser(description="회차별 설정 값 추적 (과거 이력·되돌림 확인)")
    ap.add_argument("--file", required=True, help="앱 기준 상대 경로 (예: Configuration/Ecu/Ecud_EcuM.arxml)")
    ap.add_argument("--key", action="append", required=True)
    ap.add_argument("--regex", action="store_true")
    ap.add_argument("--rev", action="append", required=True, help="'이름=루트' 를 회차 순서대로")
    ap.add_argument("--ours")
    ap.add_argument("--repo")
    ap.add_argument("--git-text")
    a = ap.parse_args()

    cols = []
    for r in a.rev:
        if "=" not in r:
            sys.exit(f"--rev 는 '이름=루트' 형식: {r}")
        name, root = r.split("=", 1)
        cols.append((name.strip(), root.strip()))
    if a.ours:
        cols.append(("당사", a.ours))

    data = []
    for name, root in cols:
        d, p = load(root, a.file)
        data.append((name, d))
        print(f"== {name}: {p or MISSING_FILE}")

    pats = [re.compile(k) for k in a.key] if a.regex else None
    def hit(key):
        return any(p.search(key) for p in pats) if pats else any(k in key for k in a.key)

    keys = sorted({k for _, d in data if d for k in d if hit(k)})
    if not keys:
        print("\n일치하는 키 없음 — 키 문자열을 확인하거나 --regex 를 쓴다")
        return

    flagged = 0
    print()
    for key in keys:
        print(f"[{key}]")
        seq = []
        for name, d in data:
            v = MISSING_FILE if d is None else d.get(key, ABSENT)
            print(f"    {name:<22} {fmt(v)}")
            if d is not None and name != "당사":
                seq.append((name, v))
        msg = regression(seq)
        if not msg and len(seq) >= 2:
            # 보정본 값이 이후 회차에서 달라짐 — 3점이 없어도 되돌림 후보 (이전 원본에 파일이 없던 경우 등)
            for i, (n, v) in enumerate(seq[:-1]):
                if any(w in n for w in ("보정", "정정", "재배포")) and seq[-1][1] != v:
                    msg = f"되돌림 후보: {n} 의 값이 마지막 회차 {seq[-1][0]} 에서 다름 — 보정이 빠진 것인지 확인"
                    break
        if msg:
            flagged += 1
            print(f"    ★ {msg}")
    print(f"\n== 요약: 키 {len(keys)}개, 되돌림 의심 {flagged}개"
          + (" — 판정표 '이력' 칸에 회차별 값을 적고 어느 쪽이 최종인지 사용자 확인 / HAE 질문(C)" if flagged else ""))

    if a.git_text:
        repo = a.repo or a.ours
        if not repo:
            sys.exit("--git-text 에는 --repo 또는 --ours 가 필요")
        r = subprocess.run(["git", "-C", repo, "log", "--format=%h %ad %s", "--date=short", "-S", a.git_text, "--", "."],
                           capture_output=True)
        out = r.stdout.decode("utf-8", "replace").strip()
        print(f"\n== 당사 git 이력 (git log -S '{a.git_text}')\n{out or '없음'}")


if __name__ == "__main__":
    main()
