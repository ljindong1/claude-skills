#!/usr/bin/env python3
"""Redmine CLI. 표준 라이브러리만 사용한다 (설치 불필요).

조회(GET)는 제한 없이 하되, 쓰기(POST/PUT)는 두 겹의 안전장치 아래에서만 한다.

  1) 소유권 — 수정·코멘트는 '내가 등록한(author) 이슈'에만 허용한다.
     남의 이슈는 스크립트가 거부한다. Redmine 권한과 무관한 자체 제약이다.
  2) 확인   — 모든 쓰기는 --yes 없이는 미리보기만 출력하고 종료코드 2로 끝난다.
     사람이 내용을 보고 승인한 뒤에야 실제로 전송된다.

삭제(DELETE)는 넣지 않았다.

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
from collections import Counter

# 윈도우 콘솔 기본 인코딩(cp949)은 em-dash 등을 못 찍어 UnicodeEncodeError 로 죽는다.
# 오류 메시지도 한글이라 stderr 까지 같이 맞춰야 거부 사유가 깨지지 않는다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

TIMEOUT = 20
CONFIRM_EXIT = 2  # 미리보기만 하고 멈췄다는 뜻. 실패(1)와 구분한다.


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


def request(method, path, params=None, body=None):
    """Redmine API 호출. 헤더 인증을 먼저 쓰고, 막히면 쿼리 파라미터로 재시도한다."""
    base, key = config()
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    qs = "?" + urllib.parse.urlencode(params) if params else ""
    url = f"{base}{path}{qs}"

    try:
        return _fetch(url, {"X-Redmine-API-Key": key}, payload, method)
    except urllib.error.HTTPError as e:
        if e.code != 401:
            _http_error(e, url)
        # 일부 설정은 헤더 인증을 막고 key= 파라미터만 허용한다.
        p = dict(params or {})
        p["key"] = key
        retry = f"{base}{path}?" + urllib.parse.urlencode(p)
        try:
            return _fetch(retry, {}, payload, method)
        except urllib.error.HTTPError as e2:
            _http_error(e2, url)
    except urllib.error.URLError as e:
        die(
            f"접속 실패: {e.reason}\n"
            f"  {base} 에 도달할 수 없습니다. 사내망 안에서 실행 중인지 확인하세요.\n"
            "  (claude.ai 웹 채팅의 샌드박스에서는 사내 주소에 접근할 수 없습니다.)"
        )


def get(path, params=None):
    return request("GET", path, params)


def _fetch(url, headers, data=None, method="GET"):
    h = {"Accept": "application/json", **headers}
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
        if not raw.strip():
            return {}  # PUT 성공은 204 No Content 로 돌아온다.
        return json.loads(raw.decode("utf-8"))


def _http_error(e, url):
    hints = {
        401: "인증 실패. API 키가 40자인지, 관리자가 'REST 웹 서비스 사용'을 켰는지 확인하세요.",
        403: "권한 없음. 해당 프로젝트에 대한 열람 또는 등록/편집 권한이 계정에 없습니다.",
        404: "대상을 찾을 수 없습니다. 번호나 식별자를 확인하세요.",
        422: "Redmine이 입력값을 거부했습니다. 아래 사유를 보세요.",
    }
    body = ""
    try:
        body = e.read().decode("utf-8", "replace")
    except Exception:
        pass

    # 422 는 {"errors": [...]} 로 사유를 준다. 잘라 버리면 원인을 못 찾는다.
    detail = body[:300]
    try:
        errs = json.loads(body).get("errors")
        if errs:
            detail = "\n".join(f"  · {x}" for x in errs)
    except Exception:
        if "<html" in body.lower():
            detail = "(HTML 응답 — Redmine이 아니라 앞단 프록시가 막았을 수 있습니다)"

    die(f"HTTP {e.code} — {hints.get(e.code, e.reason)}\n  요청: {url}\n{detail}".rstrip())


def die(msg):
    sys.stdout.flush()  # stdout은 버퍼링되고 stderr은 아니라, 안 맞추면 오류가 앞으로 튄다.
    print(f"오류: {msg}", file=sys.stderr)
    sys.exit(1)


_me = None


def me():
    global _me
    if _me is None:
        _me = get("/users/current.json")["user"]
    return _me


def issue_url(issue_id):
    return f"{config()[0]}/issues/{issue_id}"


# ---------------------------------------------------------------- 값 해석


def _resolve_named(value, items, label):
    """이름이든 id든 받아 id로 바꾼다. 애매하면 후보를 보여주고 멈춘다."""
    v = str(value).strip()
    if v.isdigit():
        return int(v)
    exact = [i for i in items if (i.get("name") or "").strip() == v]
    if len(exact) == 1:
        return exact[0]["id"]
    part = [i for i in items if v.lower() in (i.get("name") or "").lower()]
    if len(part) == 1:
        return part[0]["id"]
    if not part:
        die(f"{label} '{v}' 를 찾을 수 없습니다. meta 명령으로 목록을 확인하세요.")
    cands = ", ".join(f"{i['id']}={i['name']}" for i in part[:12])
    die(f"{label} '{v}' 가 여러 개에 걸립니다. id로 지정하세요: {cands}")


def trackers():
    return get("/trackers.json").get("trackers", [])


def statuses():
    return get("/issue_statuses.json").get("issue_statuses", [])


def priorities():
    return get("/enumerations/issue_priorities.json").get("issue_priorities", [])


def resolve_project(value):
    """식별자 문자열도 받지만 POST 본문에는 숫자 id만 넣는다 (문자열은 0으로 먹힌다)."""
    p = get(f"/projects/{value}.json")["project"]
    return p["id"], p


def project_members(project_id):
    ms = get(f"/projects/{project_id}/memberships.json", {"limit": 100}).get("memberships", [])
    return [{"id": m["user"]["id"], "name": m["user"]["name"]} for m in ms if m.get("user")]


def resolve_user(value, project_id):
    v = str(value).strip()
    if v.lower() == "me":
        return me()["id"]
    if v.isdigit():
        return int(v)
    return _resolve_named(v, project_members(project_id), "담당자")


def read_text(inline, path):
    """본문은 파일로 받는 쪽이 안전하다. 윈도우 셸에서 긴 한글 여러 줄은 깨지기 쉽다."""
    if path:
        if path == "-":
            return sys.stdin.read()
        with open(path, encoding="utf-8") as f:
            return f.read()
    return inline


def parse_cf(items):
    out = []
    for it in items or []:
        if "=" not in it:
            die(f"--cf 형식은 id=값 입니다: '{it}'")
        cid, val = it.split("=", 1)
        if not cid.strip().isdigit():
            die(f"--cf 의 id는 숫자여야 합니다: '{it}'  (meta --project 로 확인)")
        out.append({"id": int(cid), "value": val})
    return out


# ---------------------------------------------------------------- 쓰기 안전장치


def require_own(issue):
    """이 스킬은 내가 등록한 이슈만 고친다. Redmine 권한과 별개인 자체 제약이다."""
    author = issue.get("author") or {}
    if author.get("id") != me()["id"]:
        die(
            f"#{issue['id']} 는 {author.get('name', '다른 사람')}(id={author.get('id')})님이 등록한 이슈입니다.\n"
            f"  이 스킬은 내가 등록한 이슈만 수정합니다. 남의 이슈는 Redmine 화면에서 직접 작업하세요.\n"
            f"  {issue_url(issue['id'])}"
        )


def confirm_gate(yes, title, lines):
    """--yes 가 없으면 보낼 내용만 찍고 멈춘다. 종료코드 2 = 아직 아무것도 안 보냄."""
    print(f"[{title}]")
    for ln in lines:
        print(ln)
    if yes:
        print("")
        return
    print("")
    print("아직 전송하지 않았습니다. 위 내용이 맞으면 같은 명령에 --yes 를 붙여 다시 실행하세요.")
    sys.exit(CONFIRM_EXIT)


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


# ---------------------------------------------------------------- 조회 명령


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
    if args.author:
        params["author_id"] = args.author
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
    u = me()
    print(f"{u.get('firstname', '')}{u.get('lastname', '')} ({u.get('login')}) / {u.get('mail', '-')}")
    print(f"계정 id={u.get('id')}  최근 로그인: {u.get('last_login_on', '-')}")
    print("접속 정상 — API 키와 REST 설정이 모두 살아 있습니다.")


_user_names = {}


def user_name(uid):
    """사용자 id → 이름. 못 읽으면 None (권한 없는 계정일 수 있다)."""
    uid = str(uid)
    if uid not in _user_names:
        try:
            u = get(f"/users/{uid}.json")["user"]
            _user_names[uid] = f"{u.get('lastname', '')}{u.get('firstname', '')} ({u.get('login')})"
        except SystemExit:
            _user_names[uid] = None
    return _user_names[uid]


def sample_issues(project=None, tracker=None, like=None, sample=100):
    """최근 이슈를 표본으로 긁어온다. 사용자정의 필드의 실제 사용값을 알아내는 유일한 방법이다."""
    params = {"status_id": "*", "sort": "updated_on:desc"}
    if project:
        params["project_id"] = project
    if tracker:
        params["tracker_id"] = tracker
    if like:
        params["subject"] = f"~{like}"

    out, offset, total = [], 0, None
    while len(out) < sample:
        p = dict(params, offset=offset, limit=min(100, sample - len(out)))
        data = get("/issues.json", p)
        got = data.get("issues", [])
        total = data.get("total_count", 0)
        out += got
        offset += len(got)
        if not got or offset >= total:
            break
    return out, total or 0


def survey_custom_fields(issues):
    """표본에 나타난 사용자정의 필드와 값 분포. {id: {name, values(Counter)}}"""
    fields = {}
    for iss in issues:
        for c in iss.get("custom_fields", []):
            e = fields.setdefault(c["id"], {"name": c.get("name"), "values": Counter()})
            v = c.get("value")
            if v in (None, "", []):
                continue
            e["values"][" / ".join(v) if isinstance(v, list) else str(v)] += 1
    return fields


def print_custom_fields(issues, total, scope):
    print(f"\n[사용자정의 필드] 표본 {len(issues)}건 (조건에 맞는 전체 {total}건) — {scope}")
    fields = survey_custom_fields(issues)
    if not fields:
        print("  표본에서 값이 채워진 사용자정의 필드가 없습니다. --like 로 비슷한 제목의 이슈를 넓게 잡아 보세요.")
        return

    for fid in sorted(fields):
        e = fields[fid]
        vals = e["values"]
        if not vals:
            continue
        # 값이 전부 숫자면 사용자 id 필드일 가능성이 높다. 이름을 붙여줘야 고를 수 있다.
        as_user = all(v.isdigit() for v in vals) and len(vals) <= 15
        print(f"  id={fid:<4} {e['name']}  — 표본 중 {sum(vals.values())}건 기입"
              + ("  (사용자 id 필드로 보임)" if as_user else ""))
        for v, n in vals.most_common(12):
            label = f"{v}"
            if as_user:
                nm = user_name(v)
                if nm:
                    label = f"{v} = {nm}"
            print(f"      {n:>3}회  {label}")
        if len(vals) > 12:
            print(f"      ... 그 외 {len(vals) - 12}종")

    print("\n  ※ 필수 여부와 전체 허용 목록은 REST API로 알 수 없다(관리자 전용). 위는 '실제로 쓰인 값'일 뿐이다.")
    print("    생성 시 422가 나면 사유에 부족한 필수 필드가 나오고, 목록형 필드에 없는 값을 주면")
    print("    '목록에 포함되어 있지 않습니다'가 나온다. 그때 여기 분포에서 고르면 된다.")


def cmd_meta(args):
    """생성·수정에 넣을 id를 찾는 곳. 추적 80여 종, 상태 60여 종이라 눈대중은 위험하다."""
    if args.like and not args.project:
        # 프로젝트 없이 제목만으로 비슷한 이슈를 전사 범위에서 훑는 모드
        tid = _resolve_named(args.tracker, trackers(), "추적") if args.tracker else None
        issues, total = sample_issues(tracker=tid, like=args.like, sample=args.sample)
        print_custom_fields(issues, total, f"제목~{args.like}" + (f", 추적 {args.tracker}" if args.tracker else ""))
        return

    if not args.project:
        print("[추적(tracker)]")
        for t in trackers():
            print(f"  {t['id']:<4} {t['name']}")
        print("\n[우선순위(priority)]")
        for pr in priorities():
            print(f"  {pr['id']:<4} {pr['name']}")
        print("\n[상태(status)] — 전역 목록. 실제 전이 가능 여부는 추적·역할 워크플로가 정한다")
        for st in statuses():
            print(f"  {st['id']:<4} {st['name']}")
        print("\n프로젝트별 추적·담당자 후보는 meta --project <식별자> 로 보세요.")
        return

    pid, proj = resolve_project(args.project)
    detail = get(f"/projects/{pid}.json", {"include": "trackers,issue_categories"})["project"]
    print(f"{proj['name']}  (identifier={proj.get('identifier')}, id={pid})")

    print("\n[이 프로젝트의 추적]")
    for t in detail.get("trackers", []) or []:
        print(f"  {t['id']:<4} {t['name']}")

    cats = detail.get("issue_categories") or []
    if cats:
        print("\n[범주(category)]")
        for c in cats:
            print(f"  {c['id']:<4} {c['name']}")

    try:
        vers = get(f"/projects/{pid}/versions.json").get("versions", [])
        open_vers = [v for v in vers if v.get("status") == "open"]
        if open_vers:
            print("\n[버전(fixed_version)] — 열린 것만")
            for v in open_vers:
                print(f"  {v['id']:<4} {v['name']}")
    except SystemExit:
        pass  # 버전 모듈이 꺼진 프로젝트는 404 를 준다. 없는 게 정상이다.

    print("\n[담당자 후보]")
    for u in project_members(pid):
        print(f"  {u['id']:<5} {u['name']}")

    tid = _resolve_named(args.tracker, trackers(), "추적") if args.tracker else None
    issues, total = sample_issues(project=pid, tracker=tid, like=args.like, sample=args.sample)
    scope = f"프로젝트 {proj.get('identifier')}"
    if args.tracker:
        scope += f", 추적 {args.tracker}"
    if args.like:
        scope += f", 제목~{args.like}"
    print_custom_fields(issues, total, scope)


# ---------------------------------------------------------------- 쓰기 명령


def cmd_create(args):
    pid, proj = resolve_project(args.project)
    body = {"project_id": pid, "subject": args.subject}

    tk = trackers()
    tracker_id = _resolve_named(args.tracker, tk, "추적")
    body["tracker_id"] = tracker_id
    tname = next((t["name"] for t in tk if t["id"] == tracker_id), str(tracker_id))

    desc = read_text(args.description, args.description_file)
    if desc:
        body["description"] = desc

    lines = [
        f"프로젝트 : {proj['name']} (id={pid})",
        f"추적     : {tname} (id={tracker_id})",
        f"제목     : {args.subject}",
    ]

    if args.status:
        body["status_id"] = _resolve_named(args.status, statuses(), "상태")
        lines.append(f"상태     : {args.status} (id={body['status_id']})")
    if args.priority:
        body["priority_id"] = _resolve_named(args.priority, priorities(), "우선순위")
        lines.append(f"우선순위 : {args.priority} (id={body['priority_id']})")
    if args.assignee:
        body["assigned_to_id"] = resolve_user(args.assignee, pid)
        lines.append(f"담당자   : {args.assignee} (id={body['assigned_to_id']})")
    if args.category:
        body["category_id"] = int(args.category)
        lines.append(f"범주     : id={args.category}")
    if args.version:
        body["fixed_version_id"] = int(args.version)
        lines.append(f"버전     : id={args.version}")
    if args.parent:
        body["parent_issue_id"] = args.parent
        lines.append(f"상위 이슈: #{args.parent}")
    if args.start:
        body["start_date"] = args.start
        lines.append(f"시작일   : {args.start}")
    if args.due:
        body["due_date"] = args.due
        lines.append(f"마감일   : {args.due}")
    if args.done is not None:
        body["done_ratio"] = args.done
        lines.append(f"진척률   : {args.done}%")
    if args.watcher:
        body["watcher_user_ids"] = [resolve_user(w, pid) for w in args.watcher]
        lines.append(f"참조자   : {', '.join(args.watcher)}")

    cf = parse_cf(args.cf)
    if cf:
        body["custom_fields"] = cf
        lines.append("사용자정의: " + " | ".join(f"{c['id']}={c['value']}" for c in cf))

    if desc:
        lines.append("")
        lines.append("설명:")
        lines += [f"  {ln}" for ln in desc.strip().splitlines()]

    confirm_gate(args.yes, "새 이슈 생성 예정", lines)

    created = request("POST", "/issues.json", body={"issue": body})["issue"]
    print(f"생성 완료: #{created['id']}  {created.get('subject')}")
    print(issue_url(created["id"]))


def cmd_update(args):
    issue = get(f"/issues/{args.id}.json")["issue"]
    require_own(issue)

    pid = field(issue, "project", "id", default=None)
    body = {}
    lines = [
        f"대상     : #{issue['id']} {field(issue, 'subject')}",
        f"프로젝트 : {field(issue, 'project', 'name')}   등록자: {field(issue, 'author', 'name')} (나)",
        "",
    ]

    def change(label, key, new_value, shown_now):
        body[key] = new_value
        lines.append(f"{label} : {shown_now}  →  {new_value}")

    if args.subject:
        change("제목    ", "subject", args.subject, field(issue, "subject"))
    if args.status:
        sid = _resolve_named(args.status, statuses(), "상태")
        change("상태    ", "status_id", sid, f"{field(issue, 'status', 'name')}(id={field(issue, 'status', 'id')})")
    if args.priority:
        change("우선순위", "priority_id", _resolve_named(args.priority, priorities(), "우선순위"),
               field(issue, "priority", "name"))
    if args.assignee:
        clear = args.assignee.strip().lower() in ("none", "clear")
        change("담당자  ", "assigned_to_id", "" if clear else resolve_user(args.assignee, pid),
               field(issue, "assigned_to", "name"))
    if args.start:
        change("시작일  ", "start_date", args.start, field(issue, "start_date"))
    if args.due:
        change("마감일  ", "due_date", args.due, field(issue, "due_date"))
    if args.done is not None:
        change("진척률  ", "done_ratio", args.done, f"{issue.get('done_ratio', 0)}%")
    if args.version:
        change("버전    ", "fixed_version_id", int(args.version), field(issue, "fixed_version", "name"))
    if args.category:
        change("범주    ", "category_id", int(args.category), field(issue, "category", "name"))
    if args.parent:
        change("상위이슈", "parent_issue_id", args.parent, f"#{field(issue, 'parent', 'id')}")

    desc = read_text(args.description, args.description_file)
    if desc:
        body["description"] = desc
        lines.append("")
        lines.append("설명 교체(기존 본문을 덮어씁니다 — 이전 본문은 변경 이력에 남습니다):")
        lines += [f"  {ln}" for ln in desc.strip().splitlines()]

    cf = parse_cf(args.cf)
    if cf:
        body["custom_fields"] = cf
        lines.append("사용자정의: " + " | ".join(f"{c['id']}={c['value']}" for c in cf))

    note = read_text(args.note, args.note_file)
    if note:
        body["notes"] = note
        if args.private_note:
            body["private_notes"] = True
        lines.append("")
        lines.append("코멘트" + (" (비공개)" if args.private_note else "") + ":")
        lines += [f"  {ln}" for ln in note.strip().splitlines()]

    if not body:
        die("바꿀 내용이 없습니다. --subject / --status / --note 등을 지정하세요.")

    confirm_gate(args.yes, "이슈 수정 예정", lines)

    request("PUT", f"/issues/{args.id}.json", body={"issue": body})
    print(f"수정 완료: #{args.id}")
    print(issue_url(args.id))


def cmd_note(args):
    issue = get(f"/issues/{args.id}.json")["issue"]
    require_own(issue)

    text = read_text(args.text, args.file)
    if not text or not text.strip():
        die("코멘트 본문이 비어 있습니다. --text 또는 --file 로 내용을 주세요.")

    body = {"notes": text}
    if args.private:
        body["private_notes"] = True

    lines = [f"대상     : #{issue['id']} {field(issue, 'subject')}", ""]
    lines.append("코멘트" + (" (비공개)" if args.private else "") + ":")
    lines += [f"  {ln}" for ln in text.strip().splitlines()]

    confirm_gate(args.yes, "코멘트 등록 예정", lines)

    request("PUT", f"/issues/{args.id}.json", body={"issue": body})
    print(f"코멘트 등록 완료: #{args.id}")
    print(issue_url(args.id))


def find_journal(issue, journal_id):
    """이슈에서 코멘트를 찾아 돌려준다. 번호를 잘못 준 경우가 흔해 후보를 함께 보여준다."""
    journals = [j for j in issue.get("journals", []) if (j.get("notes") or "").strip()]
    for j in journals:
        if j["id"] == journal_id:
            return j
    lines = [f"#{issue['id']} 에 코멘트 id {journal_id} 가 없습니다.", "  이 이슈의 코멘트:"]
    for j in journals:
        head = (j.get("notes") or "").strip().splitlines()[0][:50]
        lines.append(f"    {j['id']}  {field(j, 'user', 'name')}  {head}")
    if not journals:
        lines.append("    (본문 있는 코멘트가 없습니다)")
    die("\n".join(lines))


def diff_lines(old, new):
    """무엇이 바뀌는지만 보여준다. 전체를 다시 읽게 하지 않는다."""
    import difflib

    d = [
        ln for ln in difflib.unified_diff(
            old.splitlines(), new.splitlines(), lineterm="", n=2,
            fromfile="현재", tofile="수정본")
    ]
    return d or ["  (내용이 같습니다 — 바뀌는 것이 없습니다)"]


def cmd_note_edit(args):
    """이미 등록된 코멘트의 본문을 고친다.

    Redmine 은 코멘트 편집 이력을 남기므로 되돌릴 수 있다. 그래도 남의 코멘트는
    건드리지 않는다 - 이슈 등록자와 별개로 코멘트 작성자가 나인지 따로 확인한다.
    """
    issue = get(f"/issues/{args.id}.json", {"include": "journals"})["issue"]
    journal = find_journal(issue, args.journal)

    author = journal.get("user") or {}
    if author.get("id") != me()["id"]:
        die(
            f"코멘트 {args.journal} 은 {author.get('name', '다른 사람')}(id={author.get('id')})님이 작성했습니다.\n"
            f"  이 스킬은 내가 작성한 코멘트만 고칩니다. {issue_url(args.id)}"
        )

    old = journal.get("notes") or ""
    text = read_text(args.text, args.file)
    if text is None or not text.strip():
        die("수정할 본문이 비어 있습니다. --text 또는 --file 로 내용을 주세요.\n"
            "  (코멘트를 비우려면 Redmine 화면에서 하세요 — 실수로 지우는 것을 막기 위함입니다.)")
    if text == old:
        die("내용이 현재와 같습니다. 바뀌는 것이 없어 중단합니다.")

    lines = [
        f"대상     : #{issue['id']} {field(issue, 'subject')}",
        f"코멘트   : {args.journal}  ({field(journal, 'user', 'name')}, {field(journal, 'created_on')})",
        f"분량     : {len(old):,}자  ->  {len(text):,}자",
        "",
        "변경 내용:",
    ]
    lines += [f"  {ln}" for ln in diff_lines(old, text)]

    confirm_gate(args.yes, "코멘트 수정 예정", lines)

    request("PUT", f"/journals/{args.journal}.json", body={"journal": {"notes": text}})
    print(f"코멘트 수정 완료: #{args.id} 의 코멘트 {args.journal}")
    print("  Redmine 에 편집 이력이 남습니다.")
    print(issue_url(args.id))


# ---------------------------------------------------------------- 진입점


def main():
    p = argparse.ArgumentParser(description="Redmine CLI (조회 + 내 이슈 생성·수정)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_json(sp):
        sp.add_argument("--json", action="store_true", help="원본 JSON 출력")
        return sp

    def add_yes(sp):
        sp.add_argument("--yes", action="store_true",
                        help="실제로 전송한다. 없으면 미리보기만 하고 종료코드 2로 멈춘다")
        return sp

    # --- 조회
    s = add_json(sub.add_parser("issue", help="이슈 상세 조회"))
    s.add_argument("id", type=int)
    s.add_argument("--notes", type=int, default=10, help="표시할 최근 코멘트 수 (기본 10)")
    s.set_defaults(func=cmd_issue)

    s = add_json(sub.add_parser("search", help="이슈 목록 검색"))
    s.add_argument("--query", help="제목 부분일치")
    s.add_argument("--project", help="프로젝트 식별자 또는 id")
    s.add_argument("--status", default="open", help="open(기본) / closed / * / 상태id")
    s.add_argument("--assignee", help="담당자 id 또는 me")
    s.add_argument("--author", help="등록자 id 또는 me (내가 만든 일감 찾기)")
    s.add_argument("--tracker", help="추적 id (버그/기능 등)")
    s.add_argument("--updated-since", help="YYYY-MM-DD 이후 갱신분")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_search)

    s = add_json(sub.add_parser("projects", help="접근 가능한 프로젝트 목록"))
    s.add_argument("--limit", type=int, default=100)
    s.set_defaults(func=cmd_projects)

    s = add_json(sub.add_parser("whoami", help="접속 확인"))
    s.set_defaults(func=cmd_whoami)

    s = sub.add_parser("meta", help="추적·상태·우선순위·담당자·사용자정의 필드 확인 (생성/수정 전에)")
    s.add_argument("--project", help="지정하면 그 프로젝트의 추적·범주·버전·담당자 후보 + 사용자정의 필드 분포")
    s.add_argument("--tracker", help="표본을 이 추적으로 좁힌다 (사용자정의 필드는 추적마다 다르다)")
    s.add_argument("--like", help="제목이 비슷한 이슈를 표본으로 삼는다. --project 없이 쓰면 전사 범위")
    s.add_argument("--sample", type=int, default=100, help="표본 이슈 수 (기본 100)")
    s.set_defaults(func=cmd_meta)

    # --- 쓰기
    s = add_yes(sub.add_parser("create", help="새 이슈 생성"))
    s.add_argument("--project", required=True, help="프로젝트 식별자 또는 id")
    s.add_argument("--tracker", required=True, help="추적 이름 또는 id")
    s.add_argument("--subject", required=True)
    s.add_argument("--description", help="짧은 본문. 긴 본문은 --description-file 을 쓸 것")
    s.add_argument("--description-file", help="UTF-8 텍스트 파일 경로 ('-' 는 stdin)")
    s.add_argument("--status", help="상태 이름 또는 id (보통 생략 — 기본 상태로 들어간다)")
    s.add_argument("--priority", help="우선순위 이름 또는 id")
    s.add_argument("--assignee", help="담당자 이름/id/me")
    s.add_argument("--category", help="범주 id")
    s.add_argument("--version", help="버전(fixed_version) id")
    s.add_argument("--parent", type=int, help="상위 이슈 번호")
    s.add_argument("--start", help="시작일 YYYY-MM-DD")
    s.add_argument("--due", help="마감일 YYYY-MM-DD")
    s.add_argument("--done", type=int, help="진척률 0~100")
    s.add_argument("--watcher", action="append", help="참조자 (여러 번 지정 가능)")
    s.add_argument("--cf", action="append", help="사용자정의 필드 id=값 (여러 번 지정 가능)")
    s.set_defaults(func=cmd_create)

    s = add_yes(sub.add_parser("update", help="내가 등록한 이슈 수정"))
    s.add_argument("id", type=int)
    s.add_argument("--subject")
    s.add_argument("--description", help="설명 전체 교체")
    s.add_argument("--description-file", help="UTF-8 텍스트 파일 경로 ('-' 는 stdin)")
    s.add_argument("--status", help="상태 이름 또는 id")
    s.add_argument("--priority", help="우선순위 이름 또는 id")
    s.add_argument("--assignee", help="담당자 이름/id/me, 해제는 none")
    s.add_argument("--category", help="범주 id")
    s.add_argument("--version", help="버전 id")
    s.add_argument("--parent", type=int, help="상위 이슈 번호")
    s.add_argument("--start", help="시작일 YYYY-MM-DD")
    s.add_argument("--due", help="마감일 YYYY-MM-DD")
    s.add_argument("--done", type=int, help="진척률 0~100")
    s.add_argument("--note", help="변경과 함께 남길 코멘트")
    s.add_argument("--note-file", help="코멘트 본문 파일 ('-' 는 stdin)")
    s.add_argument("--private-note", action="store_true", help="비공개 코멘트로 등록")
    s.add_argument("--cf", action="append", help="사용자정의 필드 id=값")
    s.set_defaults(func=cmd_update)

    s = add_yes(sub.add_parser("note", help="내가 등록한 이슈에 코멘트만 추가"))
    s.add_argument("id", type=int)
    s.add_argument("--text", help="짧은 코멘트")
    s.add_argument("--file", help="코멘트 본문 파일 ('-' 는 stdin)")
    s.add_argument("--private", action="store_true", help="비공개 코멘트")
    s.set_defaults(func=cmd_note)

    s = add_yes(sub.add_parser("note-edit", help="내가 작성한 코멘트의 본문 수정"))
    s.add_argument("id", type=int, help="이슈 번호")
    s.add_argument("--journal", type=int, required=True,
                   help="코멘트 id (issue <번호> --json 의 journals[].id)")
    s.add_argument("--text", help="짧은 본문")
    s.add_argument("--file", help="본문 파일 ('-' 는 stdin). 본문 전체를 교체한다")
    s.set_defaults(func=cmd_note_edit)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
