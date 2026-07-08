#!/usr/bin/env python3
"""마운트 0-패딩 손상 xlsx 복구 — 파일 끝의 0 블록을 잘라 zip 정합성을 되살린다.

배경(실측): 마운트 동기화 경합 시 xlsx의 뒷부분이 0으로 패딩된 채 읽히는 경우가 있다.
내부 데이터(zip 엔트리)는 온전하고 꼬리만 0이므로, 마지막 유효 바이트까지 잘라내면
EOCD(중앙 디렉토리 끝) 구조가 맞아 정상 파일이 된다. 오디트 세션 실측으로 검증된 방법.

usage:
  python repair_padded_xlsx.py <손상파일.xlsx> <복구본.xlsx>

복구 후 openpyxl 로드·시트명까지 검증한다. 실패하면(0-패딩 유형이 아니면) 종료코드 1 —
그때는 사용자에게 원본 첨부를 요청하라.
"""
import sys
import zipfile
import openpyxl

EOCD = b"PK\x05\x06"


def repair(src, out):
    import struct
    data = open(src, "rb").read()
    # 주의: 정상 xlsx도 EOCD 끝 2바이트(주석 길이)가 0이라 "끝의 0 제거" 방식은 EOCD를
    # 잘라먹는다. 대신 EOCD 시그니처를 뒤에서부터 직접 찾아 정확한 파일 끝을 계산한다.
    pos = data.rfind(EOCD)
    if pos == -1 or pos + 22 > len(data):
        print("EOCD를 찾지 못함 — 0-패딩 유형이 아님(내부 데이터 손실 가능). 원본 첨부를 요청하라")
        return 1
    clen = struct.unpack("<H", data[pos + 20:pos + 22])[0]
    exact_end = pos + 22 + clen
    if exact_end > len(data):
        print("EOCD 주석 길이가 파일 밖을 가리킴 — 손상 유형 불명. 원본 첨부를 요청하라")
        return 1
    extra = data[exact_end:]
    if extra and any(b != 0 for b in extra):
        print(f"주의: 파일 끝 여분 {len(extra):,}B에 0이 아닌 데이터 존재 — 0-패딩 유형이 아닐 수 있음(복구 시도는 계속)")
    fixed = data[:exact_end]
    open(out, "wb").write(fixed)
    # 검증
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        if bad:
            print(f"zip 엔트리 손상: {bad} — 복구 불가, 원본 첨부를 요청하라")
            return 1
    wb = openpyxl.load_workbook(out, read_only=True)
    print(f"복구 성공: {out}")
    print(f"  원본 {len(data):,}B → 유효 {exact_end:,}B (0-패딩 {len(data)-exact_end:,}B 제거)")
    print(f"  시트: {wb.sheetnames}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(repair(sys.argv[1], sys.argv[2]))
