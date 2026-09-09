#!/usr/bin/env python3
"""Redmine 조회 전용 CLI. 표준 라이브러리만 사용한다 (설치 불필요).

GET 요청만 수행한다. 생성/수정/삭제 기능은 의도적으로 넣지 않았다.

환경변수:
  REDMINE_URL      예: http://ccm.mobaseelec.com:8080
  REDMINE_API_KEY  40자 API 액세스 키
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# 윈도우 콘솔 기본 인코딩(cp949)은 em-dash 등을 못 찍어 UnicodeEncodeError 로 죽는다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TIMEOUT = 20


# ---------------------------------------------------------------- 접속


def config():
    url = (os.environ.get("REDMINE_URL") or "").rstrip("/")
    key = (os.environ.get("REDMINE_API_KEY") or "").strip()

    if not url or not key:
        die(
            "REDMINE_URL / REDMINE_API_KEY 환경변수가 필요합니다.\n"
            "  Windows:  setx REDMINE_URL \"http://호스트:8080\"\n"
            "            setx REDMINE_API_KEY \"40자키\"\n"
            "  bash:     export REDMINE_URL=... ; export REDMINE_API_KEY=..."
        )

    if len(key) != 40:
        die(
            f"API 키 길이가 {len(key)}자입니다. Redmine API 키는 정확히 40자입니다.\n"
            "  '내 계정' 화면에서 Atom 키를 가져왔거나, 값이 두 번 복사됐을 수 있습니다."
        )

    return url, key


def get(path, params=None):
    """Redmine API GET. 헤더 인증을 먼저 쓰고, 막히면 쿼리 파라미터로 재시도한다."""
    base, key = config()
    qs = "?" + urllib.parse.urlencode(params) if params else ""
    url = f"{base}{path}{qs}"

    try:
        return _fetch(url, {"X-Redmine-API-Key": key})
    except urllib.error.HTTPError as e:
        if e.code != 401:
            _http_error(e, url)
        # 일부 설정은 헤더 인증을 막고 key= 파라미터만 허용한다.
        p = dict(params or {})
        p["key"] = key
        retry = f"{base}{path}?" + urllib.parse.urlencode(p)
        try:
            return _fetch(retry, {})
        except urllib.error.HTTPError as e2:
            _http_error(e2, url)
    except urllib.error.URLError as e:
        die(
            f"접속 실패: {e.reason}\n"
            f"  {base} 에 도달할 수 없습니다. 사내망 안에서 실행 중인지 확인하세요.\n"
            "  (claude.ai 웹 채팅의 샌드박스에서는 사내 주소에 접근할 수 없습니다.)"
        )


def _fetch(url, headers):
    req = urllib.request.Request(url, headers={"Accept": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_error(e, url):
    hints = {
        401: "인증 실패. API 키가 40자인지, 관리자가 'REST 웹 서비스 사용'을 켰는지 확인하세요.",
        403: "권한 없음. 해당 프로젝트를 열람할 권한이 계정에 없습니다.",
        404: "대상을 찾을 수 없습니다. 번호나 식별자를 확인하세요.",
    }
    body = ""
    try:
        body = e.read().decode("utf-8", "replace")[:200]
    except Exception:
        pass
    if "<html" in body.lower():
        body = "(HTML 응답 — Redmine이 아니라 앞단 프록시가 막았을 수 있습니다)"
    die(f"HTTP {e.code} — {hints.get(e.code, e.reason)}\n  요청: {url}\n  {body}".rstrip())


def die(msg):
    print(f"오류: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- 출력


def field(d, *path, default="-"):
    """중첩 dict를 안전하게 파고든다. field(issue, 'status', 'name')"""
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur if cur not in (None, "") else default


def show_issue(issue, notes_limit):
    out = []
    a = out.append
    a(f"#{issue['id']}  {field(issue, 'subject')}")
    a("=" * 60)
    a(f"프로젝트 : {field(issue, 'project', 'name')}")
    a(f"추적     : {field(issue, 'tracker', 'name')}")
    a(f"상태     : {field(issue, 'status', 'name')}   우선순위: {field(issue, 'priority', 'name')}")
    a(f"담당자   : {field(issue, 'assigned_to', 'name')}   등록자: {field(issue, 'author', 'name')}")
    a(f"진척률   : {issue.get('done_ratio', 0)}%")
    a(f"기간     : {field(issue, 'start_date')} ~ {field(issue, 'due_date')}")
    a(f"생성     : {field(issue, 'created_on')}   수정: {field(issue, 'updated_on')}")

    custom = [
        f"{c.get('name')}: {c.get('value')}"
        for c in issue.get("custom_fields", [])
        if c.get("value") not in (None, "", [])
    ]
    if custom:
        a("사용자정의: " + " | ".join(custom))

    desc = (issue.get("description") or "").strip()
    if desc:
        a("")
        a("[설명]")
        a(desc)

    atts = issue.get("attachments") or []
    if atts:
        a("")
        a("[첨부]")
        for at in atts:
            size_kb = round(at.get("filesize", 0) / 1024)
            a(f"  - {at.get('filename')} ({size_kb}KB, id={at.get('id')})")

    rels = issue.get("relations") or []
    if rels:
        a("")
        a("[연관 이슈]")
        for r in rels:
            a(f"  - {r.get('relation_type')} → #{r.get('issue_to_id')}")

    notes = [j for j in (issue.get("journals") or []) if (j.get("notes") or "").strip()]
    if notes:
        a("")
        a(f"[코멘트] 총 {len(notes)}건" + (f" (최근 {notes_limit}건 표시)" if len(notes) > notes_limit else ""))
        for j in notes[-notes_limit:]:
            a("")
            a(f"  {field(j, 'user', 'name')} / {field(j, 'created_on')}")
            for line in j["notes"].strip().splitlines():
                a(f"    {line}")

    changes = [j for j in (issue.get("journals") or []) if j.get("details")]
    if changes:
        a("")
        a(f"[변경 이력] {len(changes)}건 — 상태·담당자 변경 등은 --json 으로 상세 확인")

    return "\n".join(out)


def show_list(issues, total):
    if not issues:
        return "조건에 맞는 이슈가 없습니다."
    # 한글은 글자폭이 달라 고정폭 정렬이 어긋난다. 구분자로 나눠 두고 정리는 응답에서 한다.
    rows = [f"총 {total}건 중 {len(issues)}건 표시", "id | 상태 | 담당자 | 갱신일 | 제목", "-" * 60]
    for i in issues:
        subject = field(i, "subject")
        if len(subject) > 60:
            subject = subject[:59] + "…"
        rows.append(
            f"#{i['id']} | {field(i, 'status', 'name')} | {field(i, 'assigned_to', 'name')}"
            f" | {field(i, 'updated_on')[:10]} | {subject}"
        )
    return "\n".join(rows)


# ---------------------------------------------------------------- 명령


def cmd_issue(args):
    data = get(f"/issues/{args.id}.json", {"include": "journals,attachments,relations,children"})
    issue = data["issue"]
    print(json.dumps(issue, ensure_ascii=False, indent=2) if args.json else show_issue(issue, args.notes))


def cmd_search(args):
    params = {"limit": args.limit, "sort": "updated_on:desc"}
    if args.project:
        params["project_id"] = args.project
    if args.status:
        params["status_id"] = args.status
    if args.assignee:
        params["assigned_to_id"] = args.assignee
    if args.updated_since:
        params[">=updated_on"] = args.updated_since
    if args.query:
        params["subject"] = f"~{args.query}"
    if args.tracker:
        params["tracker_id"] = args.tracker

    data = get("/issues.json", params)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(show_list(data.get("issues", []), data.get("total_count", 0)))


def cmd_projects(args):
    data = get("/projects.json", {"limit": args.limit})
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    for p in data.get("projects", []):
        print(f"{p['id']:<5} {p.get('identifier', ''):<24} {p.get('name', '')}")


def cmd_whoami(args):
    u = get("/users/current.json")["user"]
    print(f"{u.get('firstname', '')}{u.get('lastname', '')} ({u.get('login')}) / {u.get('mail', '-')}")
    print(f"계정 id={u.get('id')}  최근 로그인: {u.get('last_login_on', '-')}")
    print("접속 정상 — API 키와 REST 설정이 모두 살아 있습니다.")


def main():
    p = argparse.ArgumentParser(description="Redmine 조회 전용 CLI (읽기 전용)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_json(sp):
        sp.add_argument("--json", action="store_true", help="원본 JSON 출력")
        return sp

    s = add_json(sub.add_parser("issue", help="이슈 상세 조회"))
    s.add_argument("id", type=int)
    s.add_argument("--notes", type=int, default=10, help="표시할 최근 코멘트 수 (기본 10)")
    s.set_defaults(func=cmd_issue)

    s = add_json(sub.add_parser("search", help="이슈 목록 검색"))
    s.add_argument("--query", help="제목 부분일치")
    s.add_argument("--project", help="프로젝트 식별자 또는 id")
    s.add_argument("--status", default="open", help="open(기본) / closed / * / 상태id")
    s.add_argument("--assignee", help="담당자 id 또는 me")
    s.add_argument("--tracker", help="추적 id (버그/기능 등)")
    s.add_argument("--updated-since", help="YYYY-MM-DD 이후 갱신분")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_search)

    s = add_json(sub.add_parser("projects", help="접근 가능한 프로젝트 목록"))
    s.add_argument("--limit", type=int, default=100)
    s.set_defaults(func=cmd_projects)

    s = add_json(sub.add_parser("whoami", help="접속 확인"))
    s.set_defaults(func=cmd_whoami)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
