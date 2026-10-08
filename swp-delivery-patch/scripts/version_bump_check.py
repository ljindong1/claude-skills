#!/usr/bin/env python3
"""버전업 후 이전 버전 문자열이 남은 곳과, 새 버전 문자열이 들어간 곳을 보여 준다.

git 이 추적하는 텍스트 파일만 본다(Debug·Generated·.log·바이너리 제외).
사용:
  python version_bump_check.py <앱 또는 FBL 루트> <이전 토큰> <새 토큰> [--expect 파일 ...]
  예) python version_bump_check.py D:/Mobase/psu_master/psu_app v3_0_28 v3_0_29 --expect .project References/Doc_MB/01_CRT_UTIP_CFG/aSIMs_sample_ini.ini
--expect: 새 토큰이 반드시 들어 있어야 할 파일(프로젝트 프로필의 버전 위치 목록).
"""
import argparse, io, os, subprocess, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
EXCL = ("Debug/", "Generated/", ".log/", "Workspace/", "workspace/")
BIN = (".elf", ".hex", ".s19", ".sre", ".map", ".dla", ".dnm", ".xlsx", ".docx", ".pdf", ".zip", ".jar", ".exe", ".dll", ".png", ".bin", ".a", ".o", ".dblite", ".pyc")


def tracked(root):
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True)
    fs = r.stdout.decode("utf-8", "replace").split("\0")
    top = subprocess.run(["git", "-C", root, "rev-parse", "--show-prefix"], capture_output=True, text=True).stdout.strip()
    out = []
    for f in fs:
        if not f:
            continue
        rel = f[len(top):] if top and f.startswith(top) else f
        if rel.startswith(EXCL) or rel.lower().endswith(BIN) or rel.endswith(".log"):
            continue
        out.append(rel)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--expect", nargs="*", default=[])
    a = ap.parse_args()
    old_hits, new_hits = [], []
    for rel in tracked(a.root):
        p = os.path.join(a.root, rel)
        try:
            raw = open(p, "rb").read()
        except Exception:
            continue
        if b"\0" in raw[:8192]:
            continue  # 바이너리(빌드 캐시 등)
        t = raw.decode("utf-8", "replace")
        for i, line in enumerate(t.splitlines(), 1):
            if a.old in line:
                old_hits.append(f"{rel}:{i}: {line.strip()[:150]}")
            if a.new in line:
                new_hits.append(rel)
    print(f"== 이전 토큰 '{a.old}' 잔존 {len(old_hits)}곳")
    for h in old_hits[:50]:
        print("   " + h)
    print(f"== 새 토큰 '{a.new}' 포함 파일 {len(set(new_hits))}개")
    for f in sorted(set(new_hits)):
        print("   " + f)
    miss = [e for e in a.expect if e.replace("\\", "/") not in set(new_hits)]
    if a.expect:
        print("== 기대 위치 누락: " + (", ".join(miss) if miss else "없음"))
    print("== 판정: " + ("통과" if not old_hits and not miss else "확인 필요"))


if __name__ == "__main__":
    main()
