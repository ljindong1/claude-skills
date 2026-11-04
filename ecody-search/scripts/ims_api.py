#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eCoDY-IMS(Jira DC 10.3) 읽기 전용 조회 — 개인 액세스 토큰(PAT) 방식.

크롬(Claude in Chrome) 없이 PC 에서 바로 REST 를 호출한다. 출력 형식은
scripts/ims_search.js · ims_read.js 와 같게 맞췄으므로 선별·정독·답변 단계는 그대로다.

사용:
  python ims_api.py check
  python ims_api.py search --queries <queries.json> [--per-query 30] [--out <파일>]
  python ims_api.py read CPINFO-4186 MCP0806-298 [--max 8000] [--out <파일>]

queries.json 형식: [{"tag": "Q1", "jql": "text ~ \\"Os_Cfg\\""}, ...]
토큰: 환경변수 ECODY_IMS_TOKEN (setx 로 등록). 자세한 설명은 references/api-token.md.

[읽기 전용 가드] GET 요청만 보낸다(_ecody_common.Site.get).
"""
import argparse
import sys
import urllib.parse

from _ecody_common import Site, clip, day, emit, esc, load_queries, to_text

SEARCH_FIELDS = "summary,project,status,issuetype,created,updated,reporter,comment"
HIST_FIELDS = {"attachment", "status", "assignee", "resolution", "labels", "sprint", "duedate"}


def cmd_check(args):
    s = Site("IMS")
    j, code = s.get("/rest/api/2/myself")
    if "__error" in j:
        print(f"IMS_CHECK FAIL ({s.source}) : {j['__error']}")
        if code in (401, 403):
            print("토큰이 만료·무효이거나 권한이 없다. 토큰을 다시 발급한다(references/api-token.md).")
        return 1
    print(f"IMS_CHECK OK ({s.source}) : {j.get('displayName')} / {j.get('name')} / {s.url}")
    return 0


def cmd_search(args):
    s = Site("IMS")
    rows, log = {}, []
    for tag, jql in load_queries(args.queries, "jql"):
        if "order by" not in jql.lower():
            jql += " ORDER BY updated DESC"
        path = ("/rest/api/2/search?jql=" + urllib.parse.quote(jql, safe="")
                + f"&maxResults={args.per_query}&fields=" + urllib.parse.quote(SEARCH_FIELDS))
        j, _ = s.get(path)
        if "__error" in j:
            log.append(f"{tag} {j['__error'][:60]}")
            continue
        issues = j.get("issues") or []
        log.append(f"{tag} {len(issues)}/{j.get('total', '?')}건")
        for rank, i in enumerate(issues):
            e = rows.get(i["key"])
            if e is None:
                f = i.get("fields") or {}
                e = {"key": i["key"], "t": f.get("summary"),
                     "prj": (f.get("project") or {}).get("key"),
                     "typ": (f.get("issuetype") or {}).get("name"),
                     "st": (f.get("status") or {}).get("name"),
                     "cr": (f.get("created") or "")[:10], "up": (f.get("updated") or "")[:10],
                     "rep": (f.get("reporter") or {}).get("displayName", ""),
                     "nc": (f.get("comment") or {}).get("total", 0),
                     "hits": [], "best": 999}
                rows[i["key"]] = e
            e["hits"].append(tag)
            e["best"] = min(e["best"], rank)
    ordered = sorted(rows.values(), key=lambda e: (-len(e["hits"]), e["best"]))
    out = ["#LOG " + " / ".join(log),
           "#FORMAT 순번|키|프로젝트|유형|상태|생성|갱신|댓글수|적중쿼리|보고자|제목"]
    for i, e in enumerate(ordered, 1):
        out.append("|".join(esc(v) for v in [
            i, e["key"], e["prj"], e["typ"], e["st"], e["cr"], e["up"],
            "댓글" + str(e["nc"]), "+".join(e["hits"]), e["rep"], e["t"]]))
    emit("\n".join(out), args.out)
    return 0


def cmd_read(args):
    s = Site("IMS")
    blocks = []
    for key in args.keys:
        j, _ = s.get(f"/rest/api/2/issue/{urllib.parse.quote(key)}?expand=renderedFields,changelog")
        if "__error" in j:
            blocks.append(f"=== {key} | ERROR {j['__error'][:200]}")
            continue
        f = j.get("fields") or {}
        rf = j.get("renderedFields") or {}
        L = [f"=== {key} | {f.get('summary')}",
             "유형: {} | 상태: {} | 보고: {} | 생성: {} | 갱신: {}".format(
                 (f.get("issuetype") or {}).get("name"), (f.get("status") or {}).get("name"),
                 (f.get("reporter") or {}).get("displayName", ""),
                 day(f.get("created")), day(f.get("updated")))]
        links = []
        for l in f.get("issuelinks") or []:
            o = l.get("outwardIssue") or l.get("inwardIssue")
            if o:
                of = o.get("fields") or {}
                links.append("{}: {} {} [{}]".format((l.get("type") or {}).get("name"), o["key"],
                                                     of.get("summary"), (of.get("status") or {}).get("name")))
        subs = ["하위: {} {} [{}]".format(t["key"], (t.get("fields") or {}).get("summary"),
                                        ((t.get("fields") or {}).get("status") or {}).get("name"))
                for t in f.get("subtasks") or []]
        if f.get("parent"):
            L.append(f"상위: {f['parent']['key']} {(f['parent'].get('fields') or {}).get('summary')}")
        if links or subs:
            L += ["--- 연결"] + links + subs
        att = ["{} ({}KB, {}, {})".format(a.get("filename"), round((a.get("size") or 0) / 1024),
                                          day(a.get("created")), (a.get("author") or {}).get("displayName", ""))
               for a in f.get("attachment") or []]
        if att:
            L.append("--- 첨부: " + ", ".join(att))
        hist = []
        for h in ((j.get("changelog") or {}).get("histories") or []):
            items = [it for it in h.get("items") or [] if (it.get("field") or "").lower() in HIST_FIELDS]
            if items:
                hist.append("{} {}: ".format(day(h.get("created")), (h.get("author") or {}).get("displayName", ""))
                            + "; ".join("{} [{} → {}]".format(it.get("field"), (it.get("fromString") or "")[:60],
                                                              (it.get("toString") or "")[:60]) for it in items))
        if hist:
            L += ["--- 변경 이력 (첨부·상태·담당자 등)"] + hist
        L += ["--- 설명", to_text(rf.get("description") or f.get("description"))]
        cs = ((f.get("comment") or {}).get("comments")) or []
        rcs = ((rf.get("comment") or {}).get("comments")) or []
        L.append(f"--- 댓글 {len(cs)}건")
        for i, c in enumerate(cs):
            upd = c.get("updated")
            mark = f" (수정 {day(upd)})" if upd and upd != c.get("created") else ""
            L.append(f"## [{i}] {day(c.get('created'))} {(c.get('author') or {}).get('displayName', '')}{mark}")
            L.append(to_text((rcs[i].get("body") if i < len(rcs) else None) or c.get("body")))
        blocks.append(clip("\n".join(L), args.max))
    emit("\n\n".join(blocks), args.out)
    return 0


def main():
    ap = argparse.ArgumentParser(description="eCoDY-IMS 읽기 전용 조회 (PAT)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="토큰 확인 (/rest/api/2/myself)")
    s = sub.add_parser("search", help="JQL 여러 개 검색 → 후보 표")
    s.add_argument("--queries", required=True, help='[{"tag","jql"}] JSON 파일')
    s.add_argument("--per-query", type=int, default=30)
    s.add_argument("--out")
    r = sub.add_parser("read", help="이슈 정독 (본문·댓글·첨부·연결·이력)")
    r.add_argument("keys", nargs="+")
    r.add_argument("--max", type=int, default=8000)
    r.add_argument("--out")
    a = ap.parse_args()
    return {"check": cmd_check, "search": cmd_search, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
