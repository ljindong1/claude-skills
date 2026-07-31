#!/usr/bin/env python3
"""대상 산출물 폴더의 파일이 매핑(deliverable_map)으로 설명되는지 점검한다.

"뭔가 빠진 것 같은" 누락을 사전에 잡는 커버리지 체커.
(1) 매핑됨 (2) 잣대/타프로젝트(점검대상 아님) (3) 미매핑(확인 필요)로 분류.

usage: python coverage_check.py <대상산출물폴더> <deliverable_map.json>
"""
import sys
import os
import re
import json

# 점검 대상이 아닌 잣대/참조/타프로젝트 파일 패턴(정규화 부분문자열)
REFERENCE = ['bj1bdc', 'jx1', 'mpe1', 'mpe2', '표준', '지침서', 'pamv']


def tok(s):
    return re.sub(r'[\s_\-(),\[\]/·.]', '', os.path.splitext(s)[0]).lower()


def shared(a, b, n=6):
    return any(a[i:i + n] in b for i in range(len(a) - n + 1))


def main(folder, mappath):
    mp = json.load(open(mappath, encoding='utf-8'))
    map_tokens = [tok(v[0]) for v in mp.get('evidence', {}).values()]
    entries = os.listdir(folder)
    files = [f for f in entries if os.path.isfile(os.path.join(folder, f))]
    files += [f + '/' for f in entries
              if os.path.isdir(os.path.join(folder, f)) and not f.startswith('_')]  # 작업 폴더(_*) 제외
    mapped, ref, unmapped = [], [], []
    for f in sorted(files):
        ft = tok(f)
        if 'traceability' in ft:
            mapped.append(f + '  (추적성 체커 사용)'); continue
        if any(r in ft for r in REFERENCE):
            ref.append(f); continue
        if any(shared(ft, mt) for mt in map_tokens):
            mapped.append(f)
        else:
            unmapped.append(f)
    print(f"총 {len(files)}개 | 매핑 {len(mapped)} | 잣대/참조 {len(ref)} | 미매핑 {len(unmapped)}")
    print("\n[ 미매핑 — 확인 필요: 점검대상인데 매핑 누락? 보조/입력? ]")
    for f in unmapped:
        print('  -', f)
    print("\n[ 잣대/참조(점검대상 아님) ]")
    for f in ref:
        print('  -', f)
    return unmapped


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
