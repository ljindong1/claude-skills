# -*- coding: utf-8 -*-
"""판정표 데이터로 "끝났다"를 계산하고 일감 본문 절을 생성한다.

입력은 `three_way.py --json` 이 만든 판정표다. 사실 칸(file/key/verdict/prev/cur/ours)은
그 파일에서 그대로 읽어 쓴다 — 사람이 값을 다시 타이핑할 자리가 없다.

경로별 끝나는 조건 (decision-rules.md 0 절)
    A 스스로 확정   basis 를 비우면 basis_auto(파일:경로=현재값)를 근거로 쓴다
    B 과거 자료     basis 에 출처가 있어야 한다 — 티켓·댓글·일감·날짜
    C HAE 질문      question 이 있어야 한다. Q 번호는 여기서만 자동으로 붙는다
    D 회사 기준     basis 에 사유가 있어야 한다
    E 도구 산물     보고만 — 근거를 요구하지 않는다

손으로 더한 행 (안내·수평전개에서 온 항목)
    arxml 차이가 아닌 항목 — HAE 안내 요청, 수평전개 적용 조건, 의존 모듈 승급 — 은
    three_way 가 행을 만들지 않으므로 사람이 행을 더한다. 그때 `ours` 를 적지 말고
    `file` 과 `key` 만 적고 `--probe <당사 루트>` 를 쓴다. 값은 도구가 읽어 채운다.
    "`Ecud_Dcm.arxml` 의 설정을 본다" 를 사람 대신 도구가 하는 자리다.

사용
    python issue_table.py --table 판정표.json [--probe <당사 루트>]
                          [--md 본문절.md] [--strict]

    --strict  미결 행이 있으면 종료코드 2. S9 에서 이걸 쓴다.
    --probe   ours 가 빈 행을 실제 ARXML 에서 읽어 채우고 판정표에 되써 준다.
"""
import argparse
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PATHS = {
    "A": "스스로 확정",
    "B": "과거 자료 조사",
    "C": "HAE 질문",
    "D": "회사 기준 보류",
    "E": "도구 산물 — 보고만",
}
# B·D 의 근거는 따라갈 수 있는 출처여야 한다. 산문은 근거가 아니다.
CITE_PAT = re.compile(
    r"(MCP\d|CPINFO-\d|IA-\d|VC-\d|#\d{4,}|note-\d|댓글\s*\[?\d|"
    r"20\d\d-\d\d-\d\d|[0-9a-f]{7,40}|IM\s|SAG|§\d)"
)


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def probe(table_path, d, root):
    """ours 가 빈 행을 실제 ARXML 에서 읽어 채운다. 사람이 값을 적지 않게 하는 핵심."""
    sys.dont_write_bytecode = True  # 스킬 폴더에 __pycache__ 를 남기지 않는다
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import three_way as tw

    cache, filled, miss = {}, 0, []
    for r in d.get("rows", []):
        if r.get("kind") != "decision" or (r.get("ours") or "").strip():
            continue
        rel = r.get("file") or ""
        if rel not in cache:
            p = tw.find_in(root, rel)
            cache[rel] = tw.parse(p) if p else None
        O = cache[rel]
        if O is None:
            miss.append((r.get("id"), rel, "당사 루트에 파일이 없다"))
            continue
        key = (r.get("key") or "").strip()
        if key in O:
            val = tw.fmt(O[key])
        elif (key + "#<존재>") in O:
            val = "있음"
        else:
            # 컨테이너 경로로 적었는데 존재하지 않는 경우도 '없음'이 답이다
            val = "없음" if key.startswith("/") else None
            if val is None:
                miss.append((r.get("id"), key, "키를 찾을 수 없다 — 경로 표기를 확인하라"))
                continue
        r["ours"] = val
        r["basis_auto"] = "%s : %s = %s" % (rel, key, val)
        filled += 1
    if filled:
        json.dump(d, io.open(table_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("조회(--probe): %d 행 채움%s" % (filled, " / 판정표에 되씀" if filled else ""))
    for i, k, why in miss:
        print("  [못 읽음] %s  %s — %s" % (i, str(k)[:70], why))
    return filled


def basis_of(r):
    """빈 basis 는 A·E 에서만 basis_auto 로 메운다."""
    b = (r.get("basis") or "").strip()
    if b:
        return b, "직접"
    if r.get("path") in ("A", "E"):
        return r.get("basis_auto", ""), "자동"
    return "", "없음"


def judge(r):
    """행 하나가 끝났는지. (닫혔나, 사유) 를 돌려준다."""
    p = (r.get("path") or "").strip().upper()
    act = (r.get("action") or "").strip()
    if not p:
        return False, "경로(A~E)가 비었다"
    if p not in PATHS:
        return False, "경로 '%s' 는 A~E 가 아니다" % p
    if not act:
        return False, "처리(반영/제외/보류/질문)가 비었다"
    b, how = basis_of(r)
    if p == "C":
        if not (r.get("question") or "").strip():
            return False, "C 인데 question 이 없다 — 무엇을 물을지 적어야 한다"
        return True, "C · 질문 등록 대기"
    if p in ("B", "D"):
        if not b:
            return False, "%s 는 근거를 직접 적어야 한다 (basis_auto 로 메우지 않는다)" % p
        if not CITE_PAT.search(b):
            return False, "%s 근거에 따라갈 출처가 없다 (티켓·댓글·커밋·날짜·IM/SAG 절)" % p
        return True, "%s · %s" % (p, b[:40])
    if not b:
        return False, "A 인데 근거가 없다 (basis_auto 도 비었다)"
    return True, "A · 근거 %s" % how


def esc(v):
    return str(v or "").replace("|", "/").replace("\n", " ")


def main():
    ap = argparse.ArgumentParser(description="판정표 완결성 계산 · 일감 본문 절 생성")
    ap.add_argument("--table", required=True, help="three_way.py --json 산출물")
    ap.add_argument("--probe", help="ours 가 빈 행을 이 당사 루트에서 읽어 채운다")
    ap.add_argument("--md", help="일감 본문에 넣을 절을 이 파일로 쓴다")
    ap.add_argument("--strict", action="store_true", help="미결이 있으면 종료코드 2")
    a = ap.parse_args()

    d = load(a.table)
    if a.probe:
        probe(a.table, d, a.probe)
        print()
    rows = [r for r in d.get("rows", []) if r.get("kind") == "decision"]
    meta = d.get("meta", {})

    closed, open_rows, by_path = [], [], {}
    for r in rows:
        ok, why = judge(r)
        (closed if ok else open_rows).append((r, why))
        p = (r.get("path") or "?").strip().upper() or "?"
        by_path[p] = by_path.get(p, 0) + 1

    print("판정표 %s — 판정 대상 %d 행" % (a.table, len(rows)))
    print("  생성 %s / Cur %s" % (meta.get("generated", "-"), meta.get("cur", "-")))
    print("  경로별: " + (", ".join("%s %d" % (k, v) for k, v in sorted(by_path.items())) or "없음"))
    print("  닫힘 %d / **미결 %d**" % (len(closed), len(open_rows)))
    if open_rows:
        print()
        print("미결 — 이 상태로는 '끝났다'고 말할 수 없다")
        for r, why in open_rows:
            print("  %s %s" % (r.get("id", "?"), r.get("key", "")[:84]))
            print("       %s" % why)

    if a.md:
        buf = []
        w = buf.append
        w("### 판정표")
        w("")
        w("> 사실 칸(위치·Prev·Cur·당사)은 `three_way.py --json` 산출물에서 그대로 옮긴 것이다 "
          "— 사람이 값을 적지 않았다. 생성 %s." % meta.get("generated", "-"))
        w("")
        w("| | 위치 | 판정 | 경로 | 처리 | 당사 현재값 | 근거 |")
        w("|---|---|---|---|---|---|---|")
        for r, _ in closed:
            b, _how = basis_of(r)
            w("| %s | `%s` | %s | **%s** %s | %s | `%s` | %s |" % (
                r.get("id", ""), esc(r.get("key")), esc(r.get("verdict")),
                esc(r.get("path")), PATHS.get((r.get("path") or "").upper(), ""),
                esc(r.get("action")), esc(r.get("ours")), esc(b)))
        if open_rows:
            w("")
            w("#### 아직 닫히지 않은 행 — %d" % len(open_rows))
            w("")
            w("| | 위치 | 왜 안 닫혔나 |")
            w("|---|---|---|")
            for r, why in open_rows:
                w("| %s | `%s` | %s |" % (r.get("id", ""), esc(r.get("key")), esc(why)))
        cs = [r for r, _ in closed if (r.get("path") or "").upper() == "C"]
        w("")
        w("### 멈춰서 물을 것 — %d 건" % len(cs))
        w("")
        if cs:
            w("> C 경로만 들어온다. A·B 로 닫힌 것은 여기 오지 않는다.")
            w("")
            w("| | 무엇을 묻나 | 관련 위치 |")
            w("|---|---|---|")
            for i, r in enumerate(cs, 1):
                w("| `Q%d` | %s | `%s` |" % (i, esc(r.get("question")), esc(r.get("key"))))
        else:
            w("없다 — 모든 항목이 당사 자료로 닫혔다.")
        txt = "\n".join(buf) + "\n"
        bad = sorted({c for c in txt if ord(c) > 0xFFFF})
        if bad:
            print()
            print("경고: 4바이트 문자 %s — Redmine 에 붙이면 HTTP 500 이 난다" % " ".join(bad))
        io.open(a.md, "w", encoding="utf-8", newline="").write(txt)
        print()
        print("본문 절 저장: %s  (판정 %d 행 · 질문 %d 건)" % (a.md, len(closed), len(cs)))

    return 2 if (a.strict and open_rows) else 0


if __name__ == "__main__":
    sys.exit(main())
