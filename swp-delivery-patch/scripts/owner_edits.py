#!/usr/bin/env python3
"""모듈 폴더를 통째 교체하기 전에, 당사가 HAE 파일을 고쳐 쓰고 있는지 찾는다.

당사 폴더(Ours)와 HAE 이전 형상(Prev)의 같은 모듈 폴더를 바이트 단위로 비교한다.
다른 파일 = 당사 수정(또는 다른 버전) → 통째 교체하면 사라지므로 3-way 병합 대상이다.
--repo 를 주면 그 파일들을 바꾼 git 커밋 제목을 함께 보여 준다.

사용:
  python owner_edits.py --prev <Prev>/Static_Code/Modules/<모듈> --ours <앱>/Static_Code/Modules/<모듈> [--repo <git 루트>]
  python owner_edits.py --prev <Prev>/Static_Code --ours <앱>/Static_Code [--repo …]   # 여러 모듈을 한 번에
Prev 가 없으면(첫 회차 등) --prev 대신 --repo 만 주고 --since 로 기간을 정하면, HAE 배포 커밋 외의
커밋이 그 폴더를 바꾼 이력만 보여 준다(메시지에 'SWP 모듈 패치|Delivery_Patch|Auto commit' 이 없는 커밋).
"""
import argparse, io, os, subprocess, sys, zlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HAE_MSG = ("SWP 모듈 패치", "Delivery_Patch", "Auto commit from Jenkins", "Delivery Patch")


def files(root):
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            full = os.path.join(dp, f)
            out[os.path.relpath(full, root).replace(os.sep, "/")] = full
    return out


def crc(p):
    return zlib.crc32(open(p, "rb").read()) & 0xFFFFFFFF


def git_log(repo, path, n=5):
    try:
        r = subprocess.run(["git", "-C", repo, "log", f"-{n}", "--format=%h %ad %s", "--date=short", "--", path],
                           capture_output=True, encoding="utf-8", errors="replace")
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception as e:
        return [f"(git 실패: {e})"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev")
    ap.add_argument("--ours", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--since", default="2 years ago")
    a = ap.parse_args()

    if a.prev:
        P, O = files(a.prev), files(a.ours)
        diff = [k for k in sorted(set(P) & set(O)) if crc(P[k]) != crc(O[k])]
        only_o = sorted(set(O) - set(P))
        only_p = sorted(set(P) - set(O))
        print(f"== 비교: 같은 파일 {len(set(P) & set(O)) - len(diff)} / 다름 {len(diff)} / 당사에만 {len(only_o)} / HAE Prev 에만 {len(only_p)}")
        doc_like = (".pdf", ".docx", ".xlsx")
        real = [k for k in diff if not k.lower().endswith(doc_like)]
        for k in diff:
            tag = "문서" if k.lower().endswith(doc_like) else "★당사 수정 의심"
            print(f"[{tag}] {k}")
            if a.repo and tag != "문서":
                for l in git_log(a.repo, O[k]):
                    print(f"      {l}")
        for k in only_o[:30]:
            print(f"[당사에만] {k}")
        for k in only_p[:30]:
            print(f"[HAE Prev 에만] {k}")
        if not real and not only_o:
            print("== 판정: 당사 수정 없음 — 폴더 통째 교체 가능 (교체 후 diff -rq 로 Cur 와 바이트 일치 확인)")
        else:
            print("== 판정: 당사 수정(또는 버전 불일치) 파일 있음 — 해당 파일은 git merge-file 로 3-way 병합, 나머지만 교체")
    elif a.repo:
        r = subprocess.run(["git", "-C", a.repo, "log", f"--since={a.since}", "--format=%h|%ad|%s", "--date=short", "--name-only", "--", a.ours],
                           capture_output=True, encoding="utf-8", errors="replace")
        cur, hits = None, {}
        for line in r.stdout.splitlines():
            if "|" in line and line.count("|") >= 2:
                cur = line
            elif line.strip() and cur and not any(m in cur for m in HAE_MSG):
                hits.setdefault(line.strip(), []).append(cur.replace("|", " "))
        print(f"== HAE 배포 커밋이 아닌 커밋이 바꾼 파일 {len(hits)}개 (기간 {a.since})")
        for f, cs in sorted(hits.items()):
            print(f"[당사 수정 이력] {f}")
            for c in cs[:4]:
                print(f"      {c}")
    else:
        ap.error("--prev 또는 --repo 가 필요합니다")


if __name__ == "__main__":
    main()
