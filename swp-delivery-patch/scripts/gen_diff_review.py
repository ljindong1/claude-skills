#!/usr/bin/env python3
"""두 커밋 사이 Generated 산출물 변화를 검수용으로 요약한다.

- C/H: 생성 시각·주석 줄을 뺀 실제 변경 줄만 보여 준다.
- ARXML: UUID 와 생성 시각을 지우고 비교해 '내용 동일(UUID 만 변경)' 여부를 판정한다.
- 로그 파일은 건너뛴다.
사용:
  python gen_diff_review.py <git 루트> <이전 커밋> <새 커밋> [--path psu_app/Generated] [--lines 40]
이전 커밋 = 직전 버전의 마지막 Jenkins Auto commit, 새 커밋 = 이번 패치 빌드의 Auto commit.
"""
import argparse, io, re, subprocess, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
NOISE = re.compile(r"(GENERATED ON|Generation Time|Date\s*:|\d{2}-[A-Za-z]{3}-\d{4}|^\s*\*|^\s*/\*|^\s*//)")


def git(root, *args, binary=False):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def norm_arxml(t):
    t = re.sub(r'\s+UUID="[^"]*"', "", t)
    t = re.sub(r'<SD [^>]*GID="(?:GENERATED|TIMESTAMP|DATE)[^"]*"[^>]*>[^<]*</SD>', "", t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--path", default="Generated")
    ap.add_argument("--lines", type=int, default=40)
    a = ap.parse_args()
    names = [l for l in git(a.root, "diff", "--name-only", a.old, a.new, "--", a.path).splitlines() if l.strip()]
    names = [n for n in names if "/log/" not in n and not n.endswith((".log", ".result", ".json", ".tree")) and ".metadata" not in n and ".tresoslog" not in n]
    print(f"== 대상 {len(names)}개 파일 (로그·메타 제외)")
    for n in names:
        if n.endswith(".arxml"):
            o = norm_arxml(git(a.root, "show", f"{a.old}:{n}"))
            w = norm_arxml(git(a.root, "show", f"{a.new}:{n}"))
            print(f"[ARXML] {n}: {'내용 동일 (UUID·시각만 변경)' if o == w else '★내용 변경 — 직접 확인'}")
        elif n.endswith((".c", ".h")):
            d = git(a.root, "diff", "-U0", a.old, a.new, "--", n)
            ch = [l for l in d.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")) and not NOISE.search(l[1:]) and l[1:].strip()]
            if not ch:
                print(f"[C/H] {n}: 시각·주석만 변경")
            else:
                print(f"[C/H] {n}: 실제 변경 {len(ch)}줄")
                for l in ch[: a.lines]:
                    print("      " + l[:160])
        else:
            print(f"[기타] {n}")
    print("\n해석: 당사 설정을 바꾸지 않았는데 바뀐 C/H, 설정을 바꿨는데 그대로인 산출물은 원인을 설명할 수 있어야 한다.")


if __name__ == "__main__":
    main()
