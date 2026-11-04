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

토큰: 환경변수 ECODY_IMS_TOKEN (사용자 환경변수, setx 로 등록). 토큰 값은 화면에 출력하지 않는다.
      setx 직후에는 이미 떠 있는 Claude Code 프로세스에 반영되지 않으므로, 그 세션에서는
        $env:ECODY_IMS_TOKEN=[Environment]::GetEnvironmentVariable('ECODY_IMS_TOKEN','User')
      를 같은 명령줄 앞에 붙여 레지스트리에서 직접 읽어 쓴다.
기타 환경변수: ECODY_IMS_URL(기본 https://ecody-ims.autoever.com),
      ECODY_IMS_INSECURE=1(인증서 검증 생략), ECODY_IMS_NOPROXY=1(프록시 무시).

[읽기 전용 가드] 이 파일은 GET 요청만 보낸다. 다른 메서드는 _get() 에서 막힌다.
"""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

DEFAULT_URL = "https://ecody-ims.autoever.com"


# --------------------------------------------------------------------------- 설정
def base_url():
    return (os.environ.get("ECODY_IMS_URL") or DEFAULT_URL).rstrip("/")


def token():
    t = (os.environ.get("ECODY_IMS_TOKEN") or "").strip()
    if t:
        return t, "환경변수 ECODY_IMS_TOKEN"
    raise SystemExit(
        "TOKEN_MISSING: 환경변수 ECODY_IMS_TOKEN 이 비어 있다.\n"
        "  등록: setx ECODY_IMS_TOKEN \"<IMS 개인 액세스 토큰>\"  (발급 절차는 references/ims-token.md)\n"
        "  이미 떠 있는 세션에서 쓰려면 명령 앞에\n"
        "    $env:ECODY_IMS_TOKEN=[Environment]::GetEnvironmentVariable('ECODY_IMS_TOKEN','User');\n"
        "  를 붙인다.\n"
        "토큰 없이 진행하려면 기존 크롬 방식(scripts/ims_search.js)으로 돌아간다."
    )


def _opener():
    handlers = []
    if os.environ.get("ECODY_IMS_INSECURE") == "1":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    if os.environ.get("ECODY_IMS_NOPROXY") == "1":
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


# --------------------------------------------------------------------------- HTTP
def _get(path, tok):
    """GET 전용. path 는 /rest/... 형태."""
    url = base_url() + path
    req = urllib.request.Request(url, method="GET")
    if req.get_method() != "GET":  # 읽기 전용 가드
        raise RuntimeError("읽기 전용 스킬: GET 이외 요청 금지")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/json")
    try:
        with _opener().open(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "replace")), r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        return {"__error": f"HTTP {e.code} {body}"}, e.code
    except Exception as e:  # DNS·TLS·프록시 등
        return {"__error": f"{type(e).__name__} {e}"}, 0


# --------------------------------------------------------------------------- HTML → 텍스트
class _Text(HTMLParser):
    BLOCK = {"tr", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "div", "pre", "table", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            alt = dict(attrs).get("alt") or ""
            self.buf.append(f"[이미지:{alt}]")
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.buf.append(" | ")
        elif tag in self.BLOCK:
            self.buf.append("\n")

    def handle_data(self, data):
        self.buf.append(data)


def to_text(html):
    if not html:
        return ""
    p = _Text()
    p.feed(str(html))
    p.close()
    lines = ("".join(p.buf)).split("\n")
    out = [" ".join(s.split()).strip() for s in lines]
    return "\n".join(s for s in out if s)


def day(s):
    return s.replace("T", " ")[:16] if s else ""


def esc(s):
    return str(s if s is not None else "").replace("|", " ").replace("\n", " ")


# --------------------------------------------------------------------------- 하위명령
def cmd_check(args):
    tok, src = token()
    j, code = _get("/rest/api/2/myself", tok)
    if "__error" in j:
        print(f"IMS_CHECK FAIL ({src}) : {j['__error']}")
        if code in (401, 403):
            print("토큰이 만료·무효이거나 권한이 없다. 토큰을 다시 발급한다(references/ims-token.md).")
        return 1
    print(f"IMS_CHECK OK ({src}) : {j.get('displayName')} / {j.get('name')} / {base_url()}")
    return 0


def cmd_search(args):
    tok, src = token()
    with open(args.queries, "r", encoding="utf-8-sig") as f:
        queries = json.load(f)
    rows, log = {}, []
    for n, q in enumerate(queries, 1):
        tag = q.get("tag") or f"Q{n}"
        jql = q["jql"]
        if "order by" not in jql.lower():
            jql += " ORDER BY updated DESC"
        path = ("/rest/api/2/search?jql=" + urllib.parse.quote(jql, safe="")
                + f"&maxResults={args.per_query}"
                + "&fields=" + urllib.parse.quote("summary,project,status,issuetype,created,updated,reporter,comment"))
        j, _ = _get(path, tok)
        if "__error" in j:
            log.append(f"{tag} {j['__error'][:60]}")
            continue
        issues = j.get("issues") or []
        log.append(f"{tag} {len(issues)}/{j.get('total', '?')}건")
        for rank, i in enumerate(issues):
            f_ = i.get("fields") or {}
            e = rows.get(i["key"])
            if e is None:
                e = {
                    "key": i["key"], "t": f_.get("summary"),
                    "prj": (f_.get("project") or {}).get("key"),
                    "typ": (f_.get("issuetype") or {}).get("name"),
                    "st": (f_.get("status") or {}).get("name"),
                    "cr": (f_.get("created") or "")[:10], "up": (f_.get("updated") or "")[:10],
                    "rep": (f_.get("reporter") or {}).get("displayName", ""),
                    "nc": (f_.get("comment") or {}).get("total", 0),
                    "hits": [], "best": 999,
                }
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


HIST_FIELDS = {"attachment", "status", "assignee", "resolution", "labels", "sprint", "duedate"}


def cmd_read(args):
    tok, src = token()
    blocks = []
    for key in args.keys:
        j, _ = _get(f"/rest/api/2/issue/{urllib.parse.quote(key)}?expand=renderedFields,changelog", tok)
        if "__error" in j:
            blocks.append(f"=== {key} | ERROR {j['__error'][:200]}")
            continue
        f_ = j.get("fields") or {}
        rf = j.get("renderedFields") or {}
        L = [f"=== {key} | {f_.get('summary')}",
             "유형: {} | 상태: {} | 보고: {} | 생성: {} | 갱신: {}".format(
                 (f_.get("issuetype") or {}).get("name"),
                 (f_.get("status") or {}).get("name"),
                 (f_.get("reporter") or {}).get("displayName", ""),
                 day(f_.get("created")), day(f_.get("updated")))]
        links = []
        for l in f_.get("issuelinks") or []:
            o = l.get("outwardIssue") or l.get("inwardIssue")
            if o:
                links.append("{}: {} {} [{}]".format(
                    (l.get("type") or {}).get("name"), o["key"],
                    (o.get("fields") or {}).get("summary"),
                    ((o.get("fields") or {}).get("status") or {}).get("name")))
        subs = ["하위: {} {} [{}]".format(s["key"], (s.get("fields") or {}).get("summary"),
                                        ((s.get("fields") or {}).get("status") or {}).get("name"))
                for s in f_.get("subtasks") or []]
        if f_.get("parent"):
            L.append(f"상위: {f_['parent']['key']} {(f_['parent'].get('fields') or {}).get('summary')}")
        if links or subs:
            L += ["--- 연결"] + links + subs
        att = ["{} ({}KB, {}, {})".format(a.get("filename"), round((a.get("size") or 0) / 1024),
                                         day(a.get("created")), (a.get("author") or {}).get("displayName", ""))
               for a in f_.get("attachment") or []]
        if att:
            L.append("--- 첨부: " + ", ".join(att))
        hist = []
        for h in ((j.get("changelog") or {}).get("histories") or []):
            items = [it for it in h.get("items") or [] if (it.get("field") or "").lower() in HIST_FIELDS]
            if items:
                hist.append("{} {}: ".format(day(h.get("created")), (h.get("author") or {}).get("displayName", ""))
                            + "; ".join("{} [{} → {}]".format(it.get("field"),
                                                              (it.get("fromString") or "")[:60],
                                                              (it.get("toString") or "")[:60]) for it in items))
        if hist:
            L += ["--- 변경 이력 (첨부·상태·담당자 등)"] + hist
        L += ["--- 설명", to_text(rf.get("description") or f_.get("description"))]
        cs = ((f_.get("comment") or {}).get("comments")) or []
        rcs = ((rf.get("comment") or {}).get("comments")) or []
        L.append(f"--- 댓글 {len(cs)}건")
        for i, c in enumerate(cs):
            upd = c.get("updated")
            mark = f" (수정 {day(upd)})" if upd and upd != c.get("created") else ""
            L.append(f"## [{i}] {day(c.get('created'))} {(c.get('author') or {}).get('displayName', '')}{mark}")
            body = (rcs[i].get("body") if i < len(rcs) else None) or c.get("body")
            L.append(to_text(body))
        text = "\n".join(L)
        if len(text) > args.max:
            text = text[:args.max] + f"\n…(이하 {len(text) - args.max}자 생략)"
        blocks.append(text)
    emit("\n\n".join(blocks), args.out)
    return 0


def emit(text, out):
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"WROTE {out} ({len(text)}자)")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)


def main():
    ap = argparse.ArgumentParser(description="eCoDY-IMS 읽기 전용 조회 (PAT)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="토큰·세션 확인 (/rest/api/2/myself)")
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
