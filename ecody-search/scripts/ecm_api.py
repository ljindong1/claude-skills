#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eCoDY-ECM(Confluence DC 9.2) 읽기 전용 조회 — 개인 액세스 토큰(PAT) 방식.

크롬(Claude in Chrome) 없이 PC 에서 바로 REST 를 호출한다. 출력 형식은
scripts/ecm_search.js · ecm_read.js 와 같게 맞췄으므로 선별·정독·답변 단계는 그대로다.

사용:
  python ecm_api.py check
  python ecm_api.py search --queries <queries.json> [--per-query 25] [--out <파일>]
  python ecm_api.py read 202544012 334015765 [--max 6000] [--out <파일>]

queries.json 형식: [{"tag": "T1", "cql": "space=mclassicfaq and title ~ \\"Wdg\\" and type=page"}, ...]
토큰: 환경변수 ECODY_ECM_TOKEN (setx 로 등록). 자세한 설명은 references/api-token.md §5.

[읽기 전용 가드] GET 요청만 보낸다(_ecody_common.Site.get).
"""
import argparse
import re
import sys
import urllib.parse

from _ecody_common import Site, clip, emit, esc, kst_date, load_queries, to_text

# 조상 페이지 제목으로 그룹을 정한다. 2026-11-04 실측 트리(mclassicfaq 최상위 7개):
#   📢 Notice / 🏁 Terms of Use (ToU) / 🔧 Technical Reference(1️⃣ IM, 2️⃣ SAG) /
#   📝Autosar Module User Manual / 📚mobilgene Tool Manual / ✅ Quality & Verification / 파일 목록
# 제목에 이모지·번호 접두사가 붙어 있어 비교 전에 앞쪽 비문자를 떼어 낸다.
# 깊은(구체적인) 분류를 먼저 적어 둔다 — 먼저 걸린 것이 그룹이 된다.
ROOTS = [
    ("Integration Auditor Guide", "IA"),
    ("Validation Checker Guide", "VC"), ("Validation checker", "VC"), ("필수 통합 점검", "VC"),
    ("IM (Integration Manual)", "IM"),
    ("SAG (", "SAG"),
    ("Notice", "NOTICE"),
    ("Policy", "POLICY"), ("Quality & Verification", "POLICY"),
    ("Terms of Use", "ToU"),
    ("Autosar Module User Manual", "UM"),
    ("C Studio", "CSTUDIO"), ("mobilgene Tool Manual", "CSTUDIO"),
]
_LEAD = re.compile(r"^[^0-9A-Za-z가-힣\[(]+")


def norm(title):
    """'📢 Notice' → 'Notice', '2️⃣ SAG (SWP Application Guide)' → 'SAG (SWP …)'"""
    return _LEAD.sub("", str(title or "")).strip()


def classify(space_key, ancestors):
    if space_key != "mclassicfaq":
        return "OTHER", space_key
    titles = [norm(t) for t in ancestors]
    for needle, code in ROOTS:
        for i, t in enumerate(titles):
            hit = (t == needle) if needle in ("Notice", "Policy") else (needle in t)
            if hit:
                return code, (titles[i + 1] if i + 1 < len(titles) else "")[:30]
    return "MISC", (titles[0] if titles else "")[:30]


def cmd_check(args):
    s = Site("ECM")
    j, code = s.get("/rest/api/user/current")
    if "__error" in j:
        print(f"ECM_CHECK FAIL ({s.source}) : {j['__error']}")
        if code in (401, 403):
            print("토큰이 만료·무효이거나 권한이 없다. 토큰을 다시 발급한다(references/api-token.md).")
        return 1
    if j.get("type") != "known":
        print(f"ECM_CHECK FAIL ({s.source}) : type={j.get('type')} (익명 — 토큰이 먹지 않았다)")
        return 1
    print(f"ECM_CHECK OK ({s.source}) : {j.get('displayName')} / {j.get('username')} / {s.url}")
    return 0


def cmd_search(args):
    s = Site("ECM")
    rows, log = {}, []
    for tag, cql in load_queries(args.queries, "cql"):
        path = ("/rest/api/content/search?cql=" + urllib.parse.quote(cql, safe="")
                + f"&limit={args.per_query}&expand=" + urllib.parse.quote("space,ancestors,version"))
        j, _ = s.get(path)
        if "__error" in j:
            log.append(f"{tag} {j['__error'][:60]}")
            continue
        res = j.get("results") or []
        log.append(f"{tag} {len(res)}건")
        for rank, p in enumerate(res):
            e = rows.get(p["id"])
            if e is None:
                anc = [a.get("title") or "" for a in (p.get("ancestors") or [])]
                sp = (p.get("space") or {}).get("key")
                g, sub = classify(sp, anc)
                ver = p.get("version") or {}
                e = {"id": p["id"], "t": p.get("title"), "g": g, "sub": sub,
                     "upd": kst_date(ver.get("when")), "v": ver.get("number"),
                     "hits": [], "best": 999}
                rows[p["id"]] = e
            e["hits"].append(tag)
            e["best"] = min(e["best"], rank)
    ordered = sorted(rows.values(), key=lambda e: (-len(e["hits"]), e["best"]))
    out = ["#LOG " + " / ".join(log),
           "#FORMAT 순번|pageId|그룹|하위분류|최종수정(KST)|버전|적중쿼리|제목"]
    for i, e in enumerate(ordered, 1):
        out.append("|".join(esc(v) for v in [
            i, e["id"], e["g"], e["sub"], e["upd"], "v" + str(e["v"]), "+".join(e["hits"]), e["t"]]))
    emit("\n".join(out), args.out)
    return 0


IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg")


def cmd_read(args):
    s = Site("ECM")
    blocks = []
    for pid in args.ids:
        j, _ = s.get(f"/rest/api/content/{urllib.parse.quote(str(pid))}"
                     "?expand=" + urllib.parse.quote("body.view,version,ancestors,children.attachment"))
        if "__error" in j:
            blocks.append(f"=== {pid} | ERROR {j['__error'][:200]}")
            continue
        ver = j.get("version") or {}
        text = to_text(((j.get("body") or {}).get("view") or {}).get("value"))
        att = [a.get("title") for a in (((j.get("children") or {}).get("attachment") or {}).get("results") or [])
               if not str(a.get("title", "")).lower().endswith(IMAGE_EXT)]
        anc = [a.get("title") or "" for a in (j.get("ancestors") or [])][1:]
        head = "=== {} | {} | v{} | {} | {}".format(
            pid, j.get("title"), ver.get("number"), kst_date(ver.get("when")),
            (ver.get("by") or {}).get("displayName", ""))
        blocks.append("\n".join([head, "경로: " + " > ".join(anc),
                                 "문서첨부: " + (", ".join(a for a in att if a) or "-"),
                                 clip(text, args.max)]))
    emit("\n\n".join(blocks), args.out)
    return 0


def main():
    ap = argparse.ArgumentParser(description="eCoDY-ECM 읽기 전용 조회 (PAT)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="토큰 확인 (/rest/api/user/current)")
    s = sub.add_parser("search", help="CQL 여러 개 검색 → 후보 표")
    s.add_argument("--queries", required=True, help='[{"tag","cql"}] JSON 파일')
    s.add_argument("--per-query", type=int, default=25)
    s.add_argument("--out")
    r = sub.add_parser("read", help="페이지 정독 (본문·경로·문서첨부)")
    r.add_argument("ids", nargs="+")
    r.add_argument("--max", type=int, default=6000)
    r.add_argument("--out")
    a = ap.parse_args()
    return {"check": cmd_check, "search": cmd_search, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
