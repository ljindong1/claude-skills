#!/usr/bin/env python3
"""배포본 두 개를 파일 단위 CRC32 로 비교한다 (재배포본 판별).

이전본(old)·새본(new)은 각각 zip 파일 또는 압축을 푼 폴더. 비밀번호가 걸린 zip 도
목록의 CRC 로 비교되므로 풀 필요가 없다. 분할 압축(.z01+.zip)은 풀어 둔 폴더를 쓴다.

경로 정규화: 최상위 폴더 1단계를 떼고, 새 배포 형식의 VersionComparison/CurrentVersion/
아래 파일은 이전 형식의 같은 상대 경로(Static_Code/..., Configuration/..., Build/...)와
patch_tool/Static_Code/... 양쪽에 대응시킨다.

사용:
  python zip_crc_compare.py <old.zip|dir> <new.zip|dir> [--json out.json]
출력: 같음 / 다름 / 이전에만 / 새것에만 — 핵심(Static_Code·Configuration·Build)과
도구·문서(patch_tool·Doc·bat)를 나눠 보여 준다.
"""
import argparse, io, json, os, sys, zipfile, zlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
CORE = ("Static_Code/", "Configuration/", "Build/")
CUR = "VersionComparison/CurrentVersion/"
PREV = "VersionComparison/PreviousVersion/"


def strip_top(p):
    p = p.replace("\\", "/")
    parts = p.split("/", 1)
    return parts[1] if len(parts) == 2 else parts[0]


def load(src):
    """{상대경로: (crc, size)}"""
    out = {}
    if os.path.isdir(src):
        tops = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        base = src
        # 압축 해제 폴더가 '패키지명/' 한 단계를 더 가지면 그 아래를 기준으로
        if len(tops) == 1 and not any(f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f)) and not f.lower().endswith((".zip", ".z01", ".z02", ".1"))):
            base = os.path.join(src, tops[0])
        for dp, _, fs in os.walk(base):
            for f in fs:
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, base).replace(os.sep, "/")
                if rel.lower().endswith((".zip", ".z01", ".z02")) or rel.endswith(".zip.1"):
                    continue
                d = open(full, "rb").read()
                out[rel] = (zlib.crc32(d) & 0xFFFFFFFF, len(d))
    else:
        z = zipfile.ZipFile(src)
        for i in z.infolist():
            if i.is_dir():
                continue
            out[strip_top(i.filename)] = (i.CRC, i.file_size)
    return out


def normalize(files):
    """새 형식(VersionComparison) → 비교용 키. Previous 는 따로 돌려준다."""
    norm, prev = {}, {}
    for k, v in files.items():
        if k.startswith(CUR):
            norm[k[len(CUR):]] = v
        elif k.startswith(PREV):
            prev[k[len(PREV):]] = v
        else:
            norm[k] = v
    return norm, prev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--json")
    a = ap.parse_args()
    old, _ = normalize(load(a.old))
    new, new_prev = normalize(load(a.new))
    # 이전 형식 patch_tool/Static_Code/X 를 새 형식 Static_Code/X 와도 대응
    for k in list(old):
        if k.startswith("patch_tool/Static_Code/") and k[len("patch_tool/"):] in new and k not in new:
            new[k] = new[k[len("patch_tool/"):]]

    def bucket(k):
        return "core" if k.startswith(CORE) else "tool_doc"

    res = {"core": {"same": [], "diff": [], "only_old": [], "only_new": []},
           "tool_doc": {"same": [], "diff": [], "only_old": [], "only_new": []}}
    for k in sorted(set(old) | set(new)):
        b = res[bucket(k)]
        if k in old and k in new:
            (b["same"] if old[k][0] == new[k][0] else b["diff"]).append(k)
        elif k in old:
            b["only_old"].append(k)
        else:
            b["only_new"].append(k)

    for name, b in res.items():
        title = "패치 본체 (Static_Code·Configuration·Build)" if name == "core" else "도구·문서 (patch_tool·Doc·bat 등)"
        print(f"== {title}")
        print(f"   같음 {len(b['same'])} / 다름 {len(b['diff'])} / 이전에만 {len(b['only_old'])} / 새것에만 {len(b['only_new'])}")
        lim = 40 if name == "core" else 12
        for key, label in (("diff", "다름"), ("only_old", "이전에만"), ("only_new", "새것에만")):
            for k in b[key][:lim]:
                print(f"   [{label}] {k}")
            if len(b[key]) > lim:
                print(f"   [{label}] … 외 {len(b[key]) - lim}개")
    if new_prev:
        print(f"== 새 배포본에 VersionComparison/PreviousVersion 있음 ({len(new_prev)}개) — 3-way 의 Prev 로 사용 가능")
    core = res["core"]
    if core["only_old"]:
        verdict = "주의: 이전본에만 있는 패치 본체 파일이 있음 — 새 배포본만으로 부족할 수 있음"
    elif core["diff"]:
        # CRC 가 다르다는 것은 '개정됐다'는 뜻일 뿐, 이전본 내용이 새본에 다 들어 있다는 뜻이 아니다.
        # MCP0806-280: 09-04 Ecud_EcuM 의 Crypto ListOne 이동이 10-06 본에서 빠졌는데 CRC 대조만 보고 놓침.
        verdict = (f"보류: 내용이 다른 패치 본체 {len(core['diff'])}개 — 내용 비교 전에는 '새 배포본만 사용'으로 판정하지 않는다. "
                   "이전본에만 있는 설정이 있을 수 있음")
    else:
        verdict = "새 배포본만 사용 가능 (이전본과 패치 본체 동일, 새것에만 있는 파일만 추가)"
    print(f"== 판정: {verdict}")
    arx = [k for k in core["diff"] if k.lower().endswith(".arxml")]
    if arx:
        print("== 내용 비교 (ARXML) — 이전본=Prev, 새본=Cur 로 three_way.py 를 돌려 나온 행은 라벨과 관계없이 전부 '재배포 개정 항목'")
        print("   python three_way.py --prev <이전본 폴더> --cur <새본 폴더(또는 VersionComparison/CurrentVersion)> --ours <당사 앱> \\")
        print("          --files " + " ".join(arx))
        print("   이전본에만 있는 설정(Cur: 없음)은 철회인지 HAE 에 확인할 항목으로 올린다")
    other = [k for k in core["diff"] if not k.lower().endswith(".arxml")]
    if other:
        print("== 내용 비교 (소스 등) — git diff --no-index <이전본 파일> <새본 파일>: " + ", ".join(other[:10]))
    if a.json:
        json.dump({"result": res, "has_prev": bool(new_prev), "verdict": verdict}, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
