#!/usr/bin/env python3
"""모듈 교체가 당사 코드와 맞닿는 곳에서 깨지는지 정적으로 점검한다.

1. 당사 코드(모듈·생성물 밖의 .c/.h)가 쓰는 '<접두>_' 심볼 중 모듈 Prev/Cur 에 선언된 것을 찾고,
   선언(원형·extern·typedef·#define) 줄이 바뀌었거나 사라진 것을 보여 준다.
2. Cur 에서 새로 #if/#ifdef 에 쓰이는 '<매크로 접두>_' 매크로 중 프로젝트 어디에도 #define 되지 않은 것
   (C 전처리기가 조용히 0 으로 처리 → 의도와 다른 경로로 컴파일될 수 있음).
3. 구조체(typedef struct)의 멤버 변화 — 당사 코드가 그 타입을 쓰면 표시.

사용:
  python symbol_crosscheck.py --prev <Prev 모듈 폴더> --cur <Cur 모듈 폴더> --app <앱 루트> --prefix Dcm_ [--macro DCM_]
"""
import argparse, io, os, re, subprocess, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
EXCL = ("Static_Code/Modules/", "Generated/", "Debug/")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def strip_comments(t):
    return re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", t), flags=re.S)


def own_files(app):
    r = subprocess.run(["git", "-C", app, "ls-files", "-z"], capture_output=True)
    if r.returncode == 0 and r.stdout:
        fs = [f for f in r.stdout.decode("utf-8", "replace").split("\0") if f.endswith((".c", ".h"))]
        # git ls-files 는 저장소 루트 기준일 수 있으므로 app 하위 경로로 보정
        top = subprocess.run(["git", "-C", app, "rev-parse", "--show-prefix"], capture_output=True, text=True).stdout.strip()
        fs = [f[len(top):] if top and f.startswith(top) else f for f in fs]
    else:
        fs = []
        for dp, _, names in os.walk(app):
            for n in names:
                if n.endswith((".c", ".h")):
                    fs.append(os.path.relpath(os.path.join(dp, n), app).replace(os.sep, "/"))
    return [f for f in fs if not f.startswith(EXCL) and os.path.exists(os.path.join(app, f))]


def decls(root, prefix):
    d, structs = {}, {}
    for dp, _, fs in os.walk(root):
        for n in fs:
            if not n.endswith((".c", ".h")):
                continue
            t = strip_comments(read(os.path.join(dp, n)))
            for line in t.splitlines():
                s = re.sub(r"\s+", " ", line.strip())
                if re.match(r"(extern|typedef|#\s*define|FUNC|VAR|CONST|P2VAR|P2CONST|static)\b", s):
                    for m in re.findall(r"\b(%s[A-Za-z0-9_]+)\b" % re.escape(prefix), s):
                        d.setdefault(m, set()).add(s[:180])
            for m in re.finditer(r"typedef\s+struct\s*\w*\s*\{(.*?)\}\s*(\w+)\s*;", t, re.S):
                body = [re.sub(r"\s+", " ", x.strip()) for x in m.group(1).split(";") if x.strip() and not x.strip().startswith("#")]
                structs[m.group(2)] = body
    return d, structs


def if_macros(root, mprefix):
    s = set()
    for dp, _, fs in os.walk(root):
        for n in fs:
            if n.endswith((".c", ".h")):
                for line in read(os.path.join(dp, n)).splitlines():
                    if re.match(r"\s*#\s*(if|elif|ifdef|ifndef)\b", line):
                        s |= set(re.findall(r"\b(%s[A-Z0-9_]+)\b" % re.escape(mprefix), line))
    return s


def defined_macros(app, mprefix):
    s = set()
    for dp, dns, fs in os.walk(app):
        dns[:] = [x for x in dns if x not in (".git", "Debug")]
        for n in fs:
            if n.endswith((".h", ".c")) or n.endswith(".arxml") and n.startswith("SCons"):
                t = read(os.path.join(dp, n))
                s |= set(re.findall(r"#\s*define\s+(%s[A-Z0-9_]+)" % re.escape(mprefix), t))
                s |= set(re.findall(r"<VALUE>\s*(%s[A-Z0-9_]+)" % re.escape(mprefix), t))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", required=True)
    ap.add_argument("--cur", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--prefix", required=True, help="심볼 접두, 예: Dcm_")
    ap.add_argument("--macro", help="매크로 접두, 예: DCM_ (기본: prefix 대문자)")
    a = ap.parse_args()
    mprefix = a.macro or a.prefix.upper()

    own = own_files(a.app)
    used = {}
    for f in own:
        for m in set(re.findall(r"\b(%s[A-Za-z0-9_]+)\b" % re.escape(a.prefix), read(os.path.join(a.app, f)))):
            used.setdefault(m, set()).add(os.path.basename(f))
    d2, s2 = decls(a.prev, a.prefix)
    d4, s4 = decls(a.cur, a.prefix)
    common = sorted(s for s in used if s in d2 or s in d4)
    print(f"== 1. 당사 코드 {len(own)}개 파일이 쓰는 모듈 심볼 {len(common)}개")
    gone = [s for s in common if s in d2 and s not in d4]
    chg = [s for s in common if s in d2 and s in d4 and d2[s] != d4[s]]
    print(f"   삭제 {len(gone)} / 선언 줄 변화 {len(chg)} (같은 줄에 함께 나온 다른 선언 때문일 수 있음 — 내용 확인)")
    for s in gone:
        print(f"   [삭제] {s}  ← {sorted(used[s])}")
    for s in chg:
        print(f"   [변화] {s}  ← {sorted(used[s])}")
        for x in sorted(d2[s] - d4[s])[:3]:
            print(f"        Prev: {x}")
        for x in sorted(d4[s] - d2[s])[:3]:
            print(f"        Cur : {x}")

    print(f"\n== 2. Cur 에서 새로 #if 에 쓰이는 {mprefix}* 매크로")
    new = sorted(if_macros(a.cur, mprefix) - if_macros(a.prev, mprefix))
    defs = defined_macros(a.app, mprefix) | set(re.findall(r"#\s*define\s+(%s[A-Z0-9_]+)" % re.escape(mprefix), "\n".join(read(os.path.join(dp, n)) for dp, _, fs in os.walk(a.cur) for n in fs if n.endswith(".h"))))
    if not new:
        print("   없음")
    for m in new:
        print(f"   {'정의됨' if m in defs else '★정의 안 됨(0 으로 처리)'}  {m}")

    print("\n== 3. 구조체 멤버 변화 (당사 코드가 쓰는 타입만)")
    hit = False
    for name in sorted(set(s2) & set(s4)):
        if s2[name] != s4[name] and name in used:
            hit = True
            add = [x for x in s4[name] if x not in s2[name]]
            rm = [x for x in s2[name] if x not in s4[name]]
            pos = "끝에 추가" if s4[name][:len(s2[name])] == s2[name] else "중간 변경 — 위치 기반 초기화·memcpy 사용처 확인"
            print(f"   {name} ← {sorted(used[name])}: +{add} -{rm} ({pos})")
    if not hit:
        print("   없음")


if __name__ == "__main__":
    main()
