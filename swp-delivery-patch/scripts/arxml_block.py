#!/usr/bin/env python3
"""ARXML 컨테이너 블록 직접 편집 — mobilgene CLI / C Studio 없이 작은 설정 변경을 반영할 때.

줄 단위로 다루며 원래 줄바꿈(CRLF/LF)과 들여쓰기를 그대로 유지한다. 값 변경은 ADMIN-DATA 의
SD GID="<파라미터>" 기록값과 VALUE 를 함께 바꾼다(ODIN 도구가 다음에 열 때 값이 어긋나지 않게).

사용 (대상 파일은 수정 후 XML 파싱을 자동 확인):
  show    <파일> <ShortName> [--parent <상위 ShortName>]
  copy    --src <HAE 파일> --name <ShortName> [--src-parent <P>] --dst <당사 파일> --after <ShortName> [--dst-parent <P>]
          HAE 배포본의 컨테이너 블록을 당사 파일의 <after> 블록 뒤에 그대로 이식 (UUID 포함)
  replace --src <HAE 파일> --name <ShortName> --dst <당사 파일> [--src-parent/--dst-parent]
          같은 이름의 블록을 HAE 블록으로 통째 교체 (차이가 해당 블록 안에만 있을 때)
  delete  <파일> <ShortName> [--parent <P>]
  rename  <파일> <옛 ShortName> <새 ShortName>     (파일 전체에서 정확히 1건일 때만)
  set     <파일> <ShortName> <파라미터> <옛 값> <새 값> [--parent <P>]
          블록 안의 SD 기록값과 VALUE 를 함께 변경 (하위 컨테이너는 건드리지 않음)
--parent 는 같은 ShortName 이 여러 곳(예: ListOne / ListTwo 의 Dcm_Init)에 있을 때 위치를 고른다.
모든 쓰기 명령은 --dry 로 미리보기만 할 수 있다.
"""
import argparse
import io
import sys
import xml.dom.minidom

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def load(p):
    b = open(p, "rb").read()
    return b.decode("utf-8").replace("\r\n", "\n").split("\n"), b"\r\n" in b


def save(p, lines, crlf):
    t = "\n".join(lines)
    if crlf:
        t = t.replace("\n", "\r\n")
    open(p, "wb").write(t.encode("utf-8"))
    xml.dom.minidom.parse(p)  # 깨졌으면 예외


def find(lines, name, parent=None):
    """SHORT-NAME=name 인 ECUC-CONTAINER-VALUE 블록의 (시작, 끝) 줄 번호(0-base, 끝 포함)."""
    start = 0
    if parent:
        ps, pe = find(lines, parent)
        start, stop = ps, pe
    else:
        stop = len(lines) - 1
    hits = []
    for i in range(start, stop + 1):
        if lines[i].strip() == f"<SHORT-NAME>{name}</SHORT-NAME>" and lines[i - 1].lstrip().startswith(
            ("<ECUC-CONTAINER-VALUE", "<ECUC-MODULE-CONFIGURATION-VALUES")
        ):
            s = i - 1
            ind = lines[s][: len(lines[s]) - len(lines[s].lstrip())]
            tag = lines[s].lstrip().split()[0].split(">")[0][1:]
            for j in range(i, stop + 1):
                if lines[j] == f"{ind}</{tag}>":
                    hits.append((s, j))
                    break
    if not hits:
        sys.exit(f"블록 없음: {name}" + (f" (상위 {parent})" if parent else ""))
    if len(hits) > 1:
        sys.exit(f"'{name}' 블록이 {len(hits)}곳 — --parent 로 위치를 지정하세요 (줄 {[h[0] + 1 for h in hits]})")
    return hits[0]


def set_value(lines, s, e, param, old, new):
    # 하위 컨테이너 시작 전까지만
    sub = next((k for k in range(s + 2, e) if lines[k].lstrip().startswith("<ECUC-CONTAINER-VALUE")), e)
    n = 0
    for k in range(s, sub):
        a, b = f'GID="{param}">{old}<', f'GID="{param}">{new}<'
        if a in lines[k]:
            lines[k] = lines[k].replace(a, b)
            n += 1
        if lines[k].strip().endswith(f"/{param}</DEFINITION-REF>") and lines[k + 1].strip() == f"<VALUE>{old}</VALUE>":
            lines[k + 1] = lines[k + 1].replace(f"<VALUE>{old}</VALUE>", f"<VALUE>{new}</VALUE>")
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("show"); p.add_argument("file"); p.add_argument("name"); p.add_argument("--parent")
    p = sp.add_parser("copy")
    for a in ("--src", "--name", "--dst", "--after"):
        p.add_argument(a, required=True)
    p.add_argument("--src-parent"); p.add_argument("--dst-parent"); p.add_argument("--dry", action="store_true")
    p = sp.add_parser("replace")
    for a in ("--src", "--name", "--dst"):
        p.add_argument(a, required=True)
    p.add_argument("--src-parent"); p.add_argument("--dst-parent"); p.add_argument("--dry", action="store_true")
    p = sp.add_parser("delete"); p.add_argument("file"); p.add_argument("name"); p.add_argument("--parent"); p.add_argument("--dry", action="store_true")
    p = sp.add_parser("rename"); p.add_argument("file"); p.add_argument("old"); p.add_argument("new"); p.add_argument("--dry", action="store_true")
    p = sp.add_parser("set")
    for a in ("file", "name", "param", "old", "new"):
        p.add_argument(a)
    p.add_argument("--parent"); p.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    if a.cmd == "show":
        L, _ = load(a.file)
        s, e = find(L, a.name, a.parent)
        print(f"줄 {s + 1}~{e + 1} ({e - s + 1}줄)")
        print("\n".join(L[s : e + 1]))
        return
    if a.cmd in ("copy", "replace"):
        S, _ = load(a.src)
        ss, se = find(S, a.name, a.src_parent)
        blk = S[ss : se + 1]
        L, crlf = load(a.dst)
        if a.cmd == "copy":
            ds, de = find(L, a.after, a.dst_parent)
            L[de + 1 : de + 1] = blk
            msg = f"'{a.name}' {len(blk)}줄을 '{a.after}' 뒤(줄 {de + 2})에 이식"
        else:
            ds, de = find(L, a.name, a.dst_parent)
            msg = f"'{a.name}' {de - ds + 1}줄 → HAE 블록 {len(blk)}줄로 교체"
            L[ds : de + 1] = blk
        target = a.dst
    elif a.cmd == "delete":
        L, crlf = load(a.file)
        s, e = find(L, a.name, a.parent)
        del L[s : e + 1]
        msg, target = f"'{a.name}' {e - s + 1}줄 삭제 (줄 {s + 1}~{e + 1})", a.file
    elif a.cmd == "rename":
        L, crlf = load(a.file)
        o = f"<SHORT-NAME>{a.old}</SHORT-NAME>"
        idx = [i for i, l in enumerate(L) if l.strip() == o]
        if len(idx) != 1:
            sys.exit(f"'{a.old}' 가 {len(idx)}곳 — 정확히 1건일 때만 변경합니다")
        L[idx[0]] = L[idx[0]].replace(o, f"<SHORT-NAME>{a.new}</SHORT-NAME>")
        msg, target = f"줄 {idx[0] + 1} 이름 변경 {a.old} → {a.new} (참조처는 git grep 으로 따로 확인)", a.file
    else:  # set
        L, crlf = load(a.file)
        s, e = find(L, a.name, a.parent)
        n = set_value(L, s, e, a.param, a.old, a.new)
        if n == 0:
            sys.exit(f"'{a.name}' 블록에서 {a.param}={a.old} 를 찾지 못함")
        msg, target = f"{a.name}/{a.param} {a.old} → {a.new} ({n}곳: SD 기록값·VALUE)", a.file
    if a.dry:
        print("[미리보기] " + msg)
        return
    save(target, L, crlf)
    print(msg + f" — 저장, XML 정상, 줄바꿈 {'CRLF' if crlf else 'LF'} 유지")


if __name__ == "__main__":
    main()
