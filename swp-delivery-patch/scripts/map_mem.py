#!/usr/bin/env python3
"""GHS map 파일의 Image Summary 섹션 크기 합계로 RAM / ROM 사용량을 계산하고 두 map 을 비교한다.

주소 범위로 RAM/ROM 을 나눈다(기본값은 CYT2B 계열: RAM 0x08000000~, ROM 0x10000000~).
.debug_* 처럼 주소가 없는 섹션은 합계에서 빠진다.
사용:
  python map_mem.py <이전.map> <새.map> [--ram 0x08000000-0x09000000] [--rom 0x10000000-0x20000000]
  python map_mem.py <새.map>                      # 한 개만 계산
이전 map 은 git show <커밋>:<경로> > 파일 로 꺼낸다. 직전 회차 보고값이 그대로 재현되는지 먼저 확인할 것.
"""
import argparse, io, re, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def rng(s):
    a, b = s.split("-")
    return int(a, 16), int(b, 16)


def calc(path, ram, rom):
    t = open(path, encoding="utf-8", errors="replace").read()
    i = t.find("Image Summary")
    if i < 0:
        sys.exit(f"Image Summary 없음: {path}")
    secs, r, o = {}, 0, 0
    for m in re.finditer(r"^\s+(\S+)\s+([0-9a-fA-F]{8})\s+[0-9a-fA-F]{8}\s+(\d+)", t[i:], re.M):
        name, base, size = m.group(1), int(m.group(2), 16), int(m.group(3))
        if ram[0] <= base < ram[1]:
            r += size
            secs[name] = ("RAM", size)
        elif rom[0] <= base < rom[1]:
            o += size
            secs[name] = ("ROM", size)
    return r, o, secs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("maps", nargs="+")
    ap.add_argument("--ram", default="0x08000000-0x09000000")
    ap.add_argument("--rom", default="0x10000000-0x20000000")
    a = ap.parse_args()
    ram, rom = rng(a.ram), rng(a.rom)
    if len(a.maps) == 1:
        r, o, _ = calc(a.maps[0], ram, rom)
        print(f"RAM {r:,} Byte / ROM {o:,} Byte")
        return
    r1, o1, s1 = calc(a.maps[0], ram, rom)
    r2, o2, s2 = calc(a.maps[1], ram, rom)
    print(f"RAM  {r1:,} -> {r2:,} Byte  ({r2 - r1:+,})")
    print(f"ROM  {o1:,} -> {o2:,} Byte  ({o2 - o1:+,})")
    for k in sorted(set(s1) | set(s2)):
        a1 = s1.get(k, ("", 0))[1]
        a2 = s2.get(k, ("", 0))[1]
        if a1 != a2:
            kind = (s2.get(k) or s1.get(k))[0]
            print(f"  {kind} {k:34s} {a1:>9,} -> {a2:>9,} ({a2 - a1:+,})")


if __name__ == "__main__":
    main()
