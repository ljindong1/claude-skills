#!/usr/bin/env python3
"""생성을 끄거나 컴파일에서 뺀 모듈의 이전 생성물이 Generated/ 에 남아 있는지 찾는다.
   SCons 는 Generated/Bsw_Output 에 있는 파일을 생성 목록에 없어도 컴파일한다(More generated file … found for compile).
   그래서 모듈을 빼면 그 모듈 생성물을 지워야 한다(jenkins-flow §5, #48891 Jenkins #18).

  python gen_stale_check.py --app <앱 루트>                    # 작업 폴더 기준
  python gen_stale_check.py --app <앱 루트> --rev <커밋>       # 그 커밋 기준(git)

  대상 모듈 = Build/SCons.arxml 의 Generation/<모듈> Used=0 이거나 Compile ExcludeList 에 Static_Code/Modules/<모듈>_* 가 있는 모듈.
  찾는 파일 = Generated/ 아래 <모듈>_*.c/.h, SchM_<모듈>.h, SchM_<모듈>_Type.h, SchM_<모듈>Type.h, PduR_<모듈>.h, Rte_<모듈>*.h
  (Bswmd_*/Swcd_* arxml 은 생성기 입력으로만 쓰여 컴파일되지 않으므로 '참고'로만 보여 준다)
"""
import argparse, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from three_way import parse  # noqa: E402


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def target_modules(scons_path):
    d = parse(scons_path)
    mods, why = set(), {}
    for k, v in d.items():
        m = re.match(r".*/Generation/([^/#]+)#Used$", k)
        if m and v and all(x in ("0", "false") for x in v):
            n = m.group(1)
            if not n.startswith(("Bswmd_", "Swcd_")):
                mods.add(n); why.setdefault(n, []).append("Generation Used=0")
        if k.endswith("#ExcludeList"):
            for x in v:
                mm = re.search(r"Static_Code[\\/]+Modules[\\/]+([A-Za-z0-9]+)_R4\d", x)
                if mm:
                    mods.add(mm.group(1)); why.setdefault(mm.group(1), []).append("ExcludeList " + x)
    return mods, why


def patterns(mod):
    m = re.escape(mod)
    return [re.compile(p) for p in (rf"^{m}_.*\.(c|h)$", rf"^SchM_{m}(_Type|Type)?\.h$", rf"^PduR_{m}\.h$", rf"^Rte_{m}(_Type)?\.h$")]


def main():
    ap = argparse.ArgumentParser(description="뺀 모듈의 남은 생성물 찾기")
    ap.add_argument("--app", required=True, help="앱 루트 (Build/, Generated/ 가 있는 폴더)")
    ap.add_argument("--rev", help="git 커밋 (없으면 작업 폴더)")
    a = ap.parse_args()

    tmp = None
    if a.rev:
        top = git(a.app, "rev-parse", "--show-toplevel").strip()
        pre = git(a.app, "rev-parse", "--show-prefix").strip()
        txt = subprocess.run(["git", "-C", top, "show", f"{a.rev}:{pre}Build/SCons.arxml"], capture_output=True).stdout
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".arxml"); tmp.write(txt); tmp.close()
        scons = tmp.name
        files = [l[len(pre):] for l in git(top, "ls-tree", "-r", "--name-only", a.rev, "--", pre + "Generated").splitlines()]
    else:
        scons = os.path.join(a.app, "Build", "SCons.arxml")
        files = []
        for dp, _, fs in os.walk(os.path.join(a.app, "Generated")):
            for f in fs:
                files.append(os.path.relpath(os.path.join(dp, f), a.app).replace(os.sep, "/"))
    try:
        mods, why = target_modules(scons)
    finally:
        if tmp:
            os.unlink(tmp.name)

    print(f"== 기준: {a.rev or '작업 폴더'}")
    if not mods:
        print("== 생성을 끄거나 컴파일에서 뺀 모듈 없음 — 판정: 통과")
        return
    stale, ref = [], []
    for mod in sorted(mods):
        print(f"== 대상 모듈 {mod}: {'; '.join(why[mod])}")
        pats = patterns(mod)
        for f in files:
            b = f.rsplit("/", 1)[-1]
            if any(p.match(b) for p in pats):
                stale.append((mod, f))
            elif re.match(rf"^(Bswmd|Swcd_Bsw)_{re.escape(mod)}\.arxml$", b):
                ref.append((mod, f))
    for mod, f in stale:
        print(f"   남은 생성물  {f}")
    for mod, f in ref:
        print(f"   (참고, 컴파일 안 됨) {f}")
    print(f"== 판정: {'확인 — 남은 생성물 ' + str(len(stale)) + '개, 컴파일되면 헤더 없음 에러. 새 생성물이 include 하지 않는지 확인 후 git rm' if stale else '통과 — 남은 생성물 없음'}")


if __name__ == "__main__":
    main()
