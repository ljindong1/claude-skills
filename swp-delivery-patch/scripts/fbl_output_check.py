#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FBL 산출물 등록 점검.

References/FBL_Output/OEUK_*/ 에 등록한 FBL 세트가
  (1) 확장자가 빠지지 않았는지
  (2) 직전 버전과 이름 규칙이 같은지
  (3) FBL 빌드가 만든 것 중 옮기지 않은 것이 없는지
를 본다.

왜 있나 — 2026-11-10 비교에서 드러난 두 실수를 막기 위한 것이다.
  * .dla / .dnm 누락 : FBL 빌드는 만들었는데(Debug/ 에 그대로 있었다)
    .elf/.hex/.map/.sre 4개만 옮겨 디버그 정보 2개가 빠졌다. 빌드 설정
    문제가 아니라 복사 누락이다. 플래시 동작에는 영향이 없어 빌드·실기로는
    절대 걸리지 않는다.
  * 이름 규칙 어긋남 : OEUK_LT2 폴더의 직전 세트는 e_lt2_... 인데
    FBL 빌드 산출물 이름은 e_bj_... 이다. 그대로 복사하면 폴더와 파일의
    차종이 어긋난다.

사용
  python fbl_output_check.py --root <APP 저장소> [--fbl-root <FBL 저장소>]
                            [--exts dla,dnm,elf,hex,map,sre]
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_EXTS = "dla,dnm,elf,hex,map,sre"
VER = re.compile(r"^(?P<base>.+?)_v(?P<ver>\d+)$")


def groups(folder, exts):
    """폴더 안의 파일을 (base, ver) -> {ext} 로 묶는다."""
    out = {}
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return out
    for n in names:
        stem, dot, ext = n.rpartition(".")
        if not dot:
            continue
        ext = ext.lower()
        if ext not in exts:
            continue
        m = VER.match(stem)
        if not m:
            continue
        key = (m.group("base"), m.group("ver"))
        out.setdefault(key, set()).add(ext)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="APP 저장소 경로")
    ap.add_argument("--fbl-root", default=None, help="FBL 저장소 경로 (있으면 빌드 산출물과 대조)")
    ap.add_argument("--exts", default=DEFAULT_EXTS, help="있어야 하는 확장자 (쉼표)")
    a = ap.parse_args()

    exts = {e.strip().lower() for e in a.exts.split(",") if e.strip()}
    out_root = os.path.join(a.root, "References", "FBL_Output")
    print("# FBL 산출물 등록 점검 - %s" % os.path.abspath(a.root))
    print("")
    if not os.path.isdir(out_root):
        print("> References/FBL_Output 이 없다. 이 프로젝트는 FBL 산출물을 등록하지 않는 것일 수 있다.")
        return 0
    print("요구 확장자 : %s" % " ".join(sorted(exts)))
    print("")

    issues = 0
    print("## 1. 폴더별 등록 상태")
    print("")
    print("| 폴더 | 버전 | 등록된 이름 | 빠진 확장자 |")
    print("|---|---|---|---|")
    conv = {}
    for d in sorted(os.listdir(out_root)):
        folder = os.path.join(out_root, d)
        if not os.path.isdir(folder):
            continue
        g = groups(folder, exts)
        if not g:
            print("| %s | - | (없음) | - |" % d)
            continue
        for (base, ver) in sorted(g, key=lambda k: k[1]):
            missing = sorted(exts - g[(base, ver)])
            mark = "**" + " ".join(missing) + "**" if missing else "없음"
            if missing:
                issues += 1
            print("| %s | v%s | `%s` | %s |" % (d, ver, base, mark))
            conv.setdefault(d, []).append((ver, base))
    print("")

    print("## 2. 이름 규칙 - 직전 버전과 같은가")
    print("")
    named = 0
    for d, lst in sorted(conv.items()):
        if len(lst) < 2:
            continue
        lst = sorted(lst, key=lambda t: t[0])
        prev_ver, prev_base = lst[0]
        for ver, base in lst[1:]:
            if base != prev_base:
                named += 1
                issues += 1
                print("- ⚠ `%s` : v%s 는 `%s` 인데 v%s 는 `%s` 다 - 차종 표기가 어긋났을 수 있다"
                      % (d, prev_ver, prev_base, ver, base))
    if not named:
        print("어긋난 것 없음 (버전이 하나뿐인 폴더는 비교 대상이 아니다).")
    print("")

    if a.fbl_root:
        print("## 3. FBL 빌드가 만든 것 중 옮기지 않은 것")
        print("")
        dbg = os.path.join(a.fbl_root, "Debug")
        built = groups(dbg, exts)
        if not built:
            print("> `%s` 에서 세트를 찾지 못했다. 빌드 직후가 아니면 비어 있는 것이 정상이다." % dbg)
        else:
            registered = set()
            for lst in conv.values():
                for ver, base in lst:
                    registered.add(ver)
            print("| 빌드 산출물 | 버전 | 만들어진 확장자 | 등록된 버전인가 |")
            print("|---|---|---|---|")
            for (base, ver) in sorted(built):
                ok = "예" if ver in registered else "**아니다**"
                if ver not in registered:
                    issues += 1
                print("| `%s` | v%s | %s | %s |" % (base, ver, " ".join(sorted(built[(base, ver)])), ok))
            print("")
            print("⭐ 빌드 산출물 이름(`%s`)과 등록 폴더의 이름 규칙이 다르면 **바꿔서** 넣는다."
                  % sorted(built)[0][0])
        print("")

    print("확인 필요 %d 건." % issues)
    if issues:
        print("")
        print("빠진 확장자가 있으면 FBL 저장소 `Debug/` 에서 가져온다. `.dla`/`.dnm` 은 "
              "GHS `-dual_debug` 가 만드는 디버그 정보라 플래시 동작에 영향이 없어 "
              "**빌드·실기로는 걸리지 않는다** - 사람이 세어야 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
