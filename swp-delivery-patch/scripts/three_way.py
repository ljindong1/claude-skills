#!/usr/bin/env python3
"""HAE 이전(Prev) / HAE 현재(Cur) / 당사(Ours) ARXML 을 파라미터 단위로 3-way 판정한다.

비교 단위: '컨테이너 경로#파라미터(또는 참조) 정의명' → 값 목록(정렬, 리스트형 파라미터는 집합 취급).
컨테이너 존재 여부도 '컨테이너 경로#<존재>' 로 비교한다. UUID·ADMIN-DATA·순서는 비교하지 않는다
(Harmonize 부산물을 걸러내기 위함).

판정:
  복사가능   HAE 변경, Ours == Prev  → Cur 값을 해당 위치에만 반영
  기존충족   HAE 변경, Ours == Cur
  충돌       HAE 변경, Ours 가 Prev·Cur 와 모두 다름 → 당사 전용 여부 판단 필요
  신규파일   Ours 에 파일 없음
'다른 구성 전제(제외)'·'보류'는 스크립트가 알 수 없으므로 사람이 판정표에서 바꾼다.

사용:
  python three_way.py --prev <Prev 루트> --cur <Cur 루트> --ours <당사 앱 루트> [--files 상대경로 ...] [--md 판정표.md]
  python three_way.py --prev <Prev> --cur <Cur> --ours <앱> --check   # 적용 후: HAE 변경 중 아직 Cur 와 다른 것만
  --check 의 남은 항목은 판정표의 제외·보류·당사 구성 반영 항목과 1:1 이어야 한다(사유 없는 항목 = 누락).
  --prev 를 생략하면 2-way(Cur vs Ours)로 하고 판정을 '차이'로만 표시한다(당사 고유 차이가 전부 섞여 나옴).
리스트형 파라미터(InputFilesList 등)는 HAE 델타(Prev→Cur 추가/삭제)만으로 판정하고, 당사 고유 차이는 비고에 개수만 적는다.
순번 파라미터(…Index/Position/Order/Priority)는 '순번 목록' 절에서 Prev/Cur/Ours 순서를 나란히 보여 주고,
목록 구성이 다르면 경고한다 — 번호를 그대로 복사하지 말고 HAE 의 번호 규칙을 당사 구성에 적용하라는 뜻이다.
하위 값이 같은 '삭제+추가' 컨테이너 쌍은 '이름변경' 한 줄로 묶는다.
루트는 Build/, Configuration/ 이 들어 있는 폴더(예: VersionComparison/CurrentVersion, psu_app).
--files 를 생략하면 Prev 와 Cur 에서 내용이 다른 .arxml 을 자동으로 고른다.
"""
import argparse, io, os, sys
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SKIP_DIRS = {"Generated", "Debug", ".git", "workspace", "Workspace", ".log"}
VAL_TAGS = {"ECUC-NUMERICAL-PARAM-VALUE", "ECUC-TEXTUAL-PARAM-VALUE", "ECUC-ADD-INFO-PARAM-VALUE",
            "ECUC-REFERENCE-VALUE", "ECUC-INSTANCE-REFERENCE-VALUE"}


def local(tag):
    return tag.split("}", 1)[-1]


def parse(path):
    """{key: tuple(sorted values)}"""
    root = ET.parse(path).getroot()
    out = {}

    def child(e, name):
        for c in e:
            if local(c.tag) == name:
                return c
        return None

    def walk(e, path):
        for c in e:
            t = local(c.tag)
            if t in ("ECUC-CONTAINER-VALUE", "ECUC-MODULE-CONFIGURATION-VALUES"):
                sn = child(c, "SHORT-NAME")
                p = path + "/" + (sn.text if sn is not None else "?")
                out.setdefault(p + "#<존재>", []).append("있음")
                walk(c, p)
            elif t in VAL_TAGS:
                d = child(c, "DEFINITION-REF")
                dn = d.text.rsplit("/", 1)[-1] if d is not None and d.text else "?"
                v = child(c, "VALUE")
                if v is None:
                    v = child(c, "VALUE-REF")
                if v is None:
                    v = child(c, "VALUE-IREF")
                out.setdefault(path + "#" + dn, []).append((v.text or "").strip() if v is not None else "")
            elif t in ("ADMIN-DATA", "SHORT-NAME", "DEFINITION-REF"):
                continue
            elif t.endswith("-REF") and c.text and c.text.strip():
                # 값 컨테이너 밖의 참조 (예: EcucValueCollection 의 ECUC-MODULE-CONFIGURATION-VALUES-REF)
                out.setdefault(path + "#" + t, []).append(c.text.strip())
            else:
                walk(c, path)

    walk(root, "")
    return {k: tuple(sorted(v)) for k, v in out.items()}


def find_in(root, rel):
    p = os.path.join(root, *rel.split("/"))
    if os.path.exists(p):
        return p
    base = os.path.basename(rel)
    for dp, dns, fs in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        if base in fs:
            return os.path.join(dp, base)
    return None


def find_renames(P, C):
    """Prev 에서 사라지고 Cur 에 생긴 컨테이너 중 하위 값이 같은 쌍 → {old: new}"""
    def containers(src):
        return {k[:-len("#<존재>")] for k in src if k.endswith("#<존재>")}
    def subtree(src, path):
        return sorted((k[len(path):], v) for k, v in src.items() if k.startswith(path + "#") or k.startswith(path + "/"))
    pc, cc = containers(P), containers(C)
    gone = [x for x in pc - cc if x.rsplit("/", 1)[0] in cc or x.count("/") <= 2]
    new = [x for x in cc - pc]
    out = {}
    for g in gone:
        sg = subtree(P, g)
        for n in new:
            if n not in out.values() and n.rsplit("/", 1)[0] == g.rsplit("/", 1)[0] and subtree(C, n) == sg:
                out[g] = n
                break
    return out


def changed_files(prev, cur):
    res = []
    for dp, dns, fs in os.walk(cur):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and d != "Static_Code"]
        for f in fs:
            if not f.lower().endswith(".arxml"):
                continue
            c = os.path.join(dp, f)
            rel = os.path.relpath(c, cur).replace(os.sep, "/")
            p = find_in(prev, rel) if prev else None
            if p is None or open(p, "rb").read() != open(c, "rb").read():
                res.append(rel)
    return sorted(res)


def fmt(v, limit=6):
    if v is None:
        return "(없음)"
    if len(v) <= limit:
        return ", ".join(v) if v else "(빈 값)"
    return ", ".join(v[:limit]) + f" … ({len(v)}개)"


def setdiff(a, b):
    a, b = set(a or ()), set(b or ())
    add, rm = sorted(b - a), sorted(a - b)
    s = []
    if add:
        s.append("+" + ", +".join(add[:8]) + (" …" if len(add) > 8 else ""))
    if rm:
        s.append("-" + ", -".join(rm[:8]) + (" …" if len(rm) > 8 else ""))
    return " ".join(s)


SEQ_HINTS = ("Index", "Position", "Order", "Priority")


def is_seq(key):
    name = key.rsplit("#", 1)[-1]
    return any(h in name for h in SEQ_HINTS)


def list_verdict(p, c, o):
    """리스트형: HAE 델타(P→C 추가/삭제)만으로 판정. 당사 고유 차이는 비고로."""
    P, C, O = set(p or ()), set(c or ()), set(o or ())
    add, rm = C - P, P - C
    have_add, have_rm = add & O, rm & O
    if have_add == add and not have_rm:
        v = "기존충족"
    elif not have_add and have_rm == rm:
        v = "복사가능"
    else:
        v = "부분반영"
    own = len(O ^ P)
    note = ("HAE 델타 " + setdiff(p, c)) + (f" | 당사는 Prev 와 {own}개 다름(당사 고유 — 델타만 반영)" if own else "")
    return v, note


def seq_views(P, C, O, skip=()):
    """순번 파라미터를 가진 상위 리스트별로 Prev/Cur/Ours 순서를 만든다. skip: 이름변경으로 처리한 컨테이너."""
    parents = {}
    for src_name, src in (("P", P or {}), ("C", C), ("O", O)):
        for k, v in src.items():
            if is_seq(k) and "#" in k:
                cpath, pname = k.rsplit("#", 1)
                parent, child = cpath.rsplit("/", 1)
                parents.setdefault((parent, pname), {}).setdefault(src_name, []).append((v[0] if v else "", child))
    out = []
    for (parent, pname), d in sorted(parents.items()):
        if any(parent == s or parent.startswith(s + "/") for s in skip):
            continue
        def order(x):
            return [f"{c}={i}" for i, c in sorted(d.get(x, []), key=lambda t: (int(t[0]) if t[0].isdigit() else 9999, t[1]))]
        po, co, oo = order("P"), order("C"), order("O")
        if P is not None and po == co:
            continue  # HAE 가 바꾸지 않은 목록은 당사 고유 구성 — 대상 아님
        if po == co and co == oo:
            continue
        if not d.get("C"):
            continue  # HAE 에서 사라진 목록(이름변경 등)은 본문 판정으로
        cset = {c for _, c in d.get("C", [])}
        oset = {c for _, c in d.get("O", [])}
        warn = ""
        if cset != oset:
            warn = f"구성 다름 — HAE 에만 {sorted(cset - oset)}, 당사에만 {sorted(oset - cset)}: 번호를 그대로 복사하지 말고 HAE 의 번호 규칙(예: 0부터 순차)을 당사 구성에 적용"
        out.append((parent, pname, po, co, oo, warn))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev")
    ap.add_argument("--cur", required=True)
    ap.add_argument("--ours", required=True)
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--md")
    ap.add_argument("--check", action="store_true", help="적용 후 Ours 와 Cur 의 남은 차이만")
    ap.add_argument("--max", type=int, default=60, help="파일당 출력 행 수 한도")
    a = ap.parse_args()

    files = a.files or changed_files(a.prev, a.cur)
    rows, summary, seq_rows = [], {}, []
    for rel in files:
        cpath = find_in(a.cur, rel)
        opath = find_in(a.ours, rel)
        ppath = find_in(a.prev, rel) if a.prev else None
        if cpath is None:
            print(f"[건너뜀] Cur 에 없음: {rel}")
            continue
        if opath is None:
            rows.append((rel, "(파일)", "신규파일", "-", "있음", "없음", ""))
            summary["신규파일"] = summary.get("신규파일", 0) + 1
            continue
        C, O = parse(cpath), parse(opath)
        P = parse(ppath) if ppath else None
        keys = sorted(set(C) | set(O) | (set(P) if P else set()))
        n = 0
        renames = find_renames(P, C) if P is not None else {}
        covered = set()
        for old, new in renames.items():
            o_has_old = (old + "#<존재>") in O
            o_has_new = (new + "#<존재>") in O
            v = "기존충족" if (o_has_new and not o_has_old) else ("복사가능" if o_has_old and not o_has_new else "충돌")
            covered.update(k for k in keys if k.startswith(old + "#") or k.startswith(old + "/") or k.startswith(new + "#") or k.startswith(new + "/"))
            if a.check and v == "기존충족":
                continue
            summary["이름변경·" + v] = summary.get("이름변경·" + v, 0) + 1
            n += 1
            rows.append((rel, f"{old} → {new.rsplit('/', 1)[-1]}", "이름변경·" + v, "있음", "있음(새 이름)",
                         "새 이름" if o_has_new else ("옛 이름" if o_has_old else "없음"), "하위 값 동일 — 이름(ShortName)만 변경, 참조처 git grep 확인"))
        for k in keys:
            if k in covered:
                continue
            c, o = C.get(k), O.get(k)
            p = P.get(k) if P is not None else None
            if P is None:
                if o == c:
                    continue
                verdict = "차이"
            else:
                if p == c:
                    continue
                if a.check and o == c:
                    continue
                multi = max(len(p or ()), len(c or ()), len(o or ())) > 1
                if multi:
                    verdict, note = list_verdict(p, c, o)
                else:
                    verdict = "기존충족" if o == c else ("복사가능" if o == p else "충돌")
                    note = ""
                if is_seq(k):
                    verdict = "순번확인"
                    note = "순번 파라미터 — 아래 '순번 목록' 절에서 목록 구성과 함께 판단"
            if a.check and verdict == "기존충족":
                continue  # --check: 반영된 것은 숨기고 남은 것만
            summary[verdict] = summary.get(verdict, 0) + 1
            n += 1
            if n <= a.max:
                if P is None:
                    note = setdiff(o, c) if max(len(c or ()), len(o or ())) > 1 else ""
                rows.append((rel, k, verdict, fmt(p) if P is not None else "-", fmt(c), fmt(o), note))
        if n > a.max:
            rows.append((rel, f"… 외 {n - a.max}행", "", "", "", "", ""))
        if n == 0:
            rows.append((rel, "(차이 없음)", "기존충족" if not a.check else "일치", "", "", "", ""))
        for parent, pname, po, co, oo, warn in seq_views(P, C, O, skip=list(renames) + list(renames.values())):
            seq_rows.append((rel, parent, pname, po, co, oo, warn))

    print("== 요약: " + ", ".join(f"{k} {v}" for k, v in sorted(summary.items())) if summary else "== 요약: 차이 없음")
    cur_file = None
    for r in rows:
        if r[0] != cur_file:
            cur_file = r[0]
            print(f"\n### {cur_file}")
        rel, k, v, p, c, o, note = r
        print(f"[{v}] {k}\n      Prev: {p}\n      Cur : {c}\n      Ours: {o}" + (f"\n      변화: {note}" if note else ""))
    if seq_rows:
        print("\n### 순번 목록 (Prev / Cur / Ours — 번호 순)")
        for rel, parent, pname, po, co, oo, warn in seq_rows:
            print(f"[{rel}] {parent}  ({pname})\n      Prev: {' , '.join(po) or '-'}\n      Cur : {' , '.join(co)}\n      Ours: {' , '.join(oo)}" + (f"\n      ⚠ {warn}" if warn else ""))
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write("| 파일 | 위치 | 판정 | Prev | Cur | Ours | 비고 |\n|---|---|---|---|---|---|---|\n")
            for r in rows:
                f.write("| " + " | ".join(x.replace("|", "/") for x in r) + " |\n")
            if seq_rows:
                f.write("\n| 파일 | 순번 목록 | Prev | Cur | Ours | 경고 |\n|---|---|---|---|---|---|\n")
                for rel, parent, pname, po, co, oo, warn in seq_rows:
                    f.write(f"| {rel} | {parent} ({pname}) | {', '.join(po)} | {', '.join(co)} | {', '.join(oo)} | {warn} |\n")
        print(f"\n판정표 저장: {a.md}")


if __name__ == "__main__":
    main()
