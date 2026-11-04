#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eCoDY-ECM 일일 변경 수집·정독 — 개인 액세스 토큰(PAT) 방식.

크롬(Claude in Chrome) 없이 PC 에서 바로 REST 를 호출한다. 출력 형식은
collect.js + dump.js · read_pages.js 와 같게 맞췄으므로 M4 이후 단계는 그대로다.

사용:
  python ecm_monitor.py collect --start <ISO UTC> --end <ISO UTC> --out <파일>
  python ecm_monitor.py read --start <ISO UTC> --jobs <jobs.json> [--max 2500] --out <파일>

jobs.json 형식: [{"id": "380196632", "mode": "body"}, {"id": "319465743", "mode": "diff"}]
토큰: 환경변수 ECODY_ECM_TOKEN (setx 로 등록). 발급·등록은 ecody-search 스킬의
      references/api-token.md 와 같다. 토큰이 없거나 401 이면 크롬 폴백
      (collect.js / dump.js / read_pages.js)으로 돌아간다.

[읽기 전용 가드] GET 요청만 보낸다(_ecody_common.Site.get).
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse

from _ecody_common import Site, emit, esc, to_text

# --------------------------------------------------------------------------- 분류
# 2026-11-04 실측 트리(mclassicfaq 최상위): 📢 Notice / 🏁 Terms of Use (ToU) /
# 🔧 Technical Reference(1️⃣ IM, 2️⃣ SAG) / 📝Autosar Module User Manual /
# 📚mobilgene Tool Manual / ✅ Quality & Verification / 파일 목록.
# 제목에 이모지·번호 접두사가 붙어 있어 비교 전에 앞쪽 비문자를 떼어 낸다.
# ecody-search/scripts/ecm_api.py 와 같은 표 — 한쪽을 고치면 다른 쪽도 고친다.
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
ORDER = ["NOTICE", "POLICY", "IA", "VC", "SAG", "IM", "UM", "CSTUDIO", "ToU", "OTHER", "MISC"]


def norm(title):
    return _LEAD.sub("", str(title or "")).strip()


def classify(space_key, anc_titles):
    if space_key != "mclassicfaq":
        return "OTHER", space_key
    titles = [norm(t) for t in anc_titles]
    for needle, code in ROOTS:
        for i, t in enumerate(titles):
            hit = (t == needle) if needle in ("Notice", "Policy") else (needle in t)
            if hit:
                return code, (titles[i + 1] if i + 1 < len(titles) else "")[:30]
    return "MISC", (titles[0] if titles else "")[:30]


RE_R = re.compile(r"\b(R4[04X]|R4x)\b", re.I)
RE_MCU = re.compile(r"\b(CYT\w*|TC[23]\w*|S32K\w*|S32G\w*|SPC58\w*|F1KM?[\w-]*|U2A\w*|RCAR\w*|U5L|RH850\w*)", re.I)
RE_MOD1 = re.compile(r"^\s*(?:\[[^\]]*\]\s*)*?\[([A-Za-z][A-Za-z0-9_]{1,15})\]")
RE_MOD2 = re.compile(r"^([A-Za-z][A-Za-z0-9_]{1,15}) - \d")
RE_MOD_SKIP = re.compile(r"^(R4|IA|VC|SAG|TASK|Patch|Package|FEATURE|V\.C)", re.I)


def tags(title):
    title = title or ""
    out = []
    m = RE_R.search(title)
    if m:
        out.append(m.group(1).upper())
    m = RE_MCU.search(title)
    if m:
        out.append(m.group(1))
    m = RE_MOD1.match(title) or RE_MOD2.match(title)
    if m and not RE_MOD_SKIP.match(m.group(1)):
        out.append(m.group(1))
    return ",".join(out)


# --------------------------------------------------------------------------- 시각
def iso(s):
    """Confluence 시각 문자열 → UTC aware datetime."""
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d.astimezone(dt.timezone.utc)


def kst(s):
    """UTC 시각 → 'MM-DD HH:MM' (KST)."""
    d = iso(s)
    return d.astimezone(dt.timezone(dt.timedelta(hours=9))).strftime("%m-%d %H:%M") if d else ""


# --------------------------------------------------------------------------- 수집
EXPAND = {
    "page": "version,history,space,ancestors",
    "blogpost": "version,history,space,ancestors",
    "comment": "version,space,container,container.ancestors",
    "attachment": "version,space,container,container.ancestors",
}
IMAGE_RE = re.compile(r"\.(png|jpe?g|gif|bmp|svg|webp)$", re.I)


def sweep(site, typ, since):
    """lastmodified >= since 인 해당 형식 전체. 200건 제한이라 _links.next 로 넘긴다."""
    path = ("/rest/api/content/search?cql="
            + urllib.parse.quote(f'lastmodified >= "{since}" and type={typ}', safe="")
            + "&limit=100&expand=" + urllib.parse.quote(EXPAND[typ]))
    out, guard = [], 0
    while path and guard < 100:
        guard += 1
        j, _ = site.get(path)
        if "__error" in j:
            raise RuntimeError(f"{typ} {j['__error'][:120]}")
        res = j.get("results") or []
        out += res
        nxt = (j.get("_links") or {}).get("next")
        path = nxt if (nxt and res) else None
    return out


def cmd_collect(args):
    site = Site("ECM")
    ws, we = iso(args.start), iso(args.end)
    if not ws or not we:
        raise SystemExit("ERROR: --start/--end 가 ISO UTC 형식이 아니다 (예 2026-11-04T06:00:00Z)")
    # CQL 날짜는 서버 시간대로 해석되므로 하루 앞당겨 넉넉히 받고 version.when 으로 정밀 필터한다.
    since = (ws - dt.timedelta(days=1)).strftime("%Y/%m/%d 00:00")
    raw = {}
    data = {}
    for typ in ("page", "blogpost", "comment", "attachment"):
        data[typ] = sweep(site, typ, since)
        raw[{"page": "page", "blogpost": "blog", "comment": "comment", "attachment": "attachment"}[typ]] = len(data[typ])

    def in_win(when):
        d = iso(when)
        return bool(d) and ws < d <= we

    rows, img_by, img_count = [], {}, 0
    for p in data["page"] + data["blogpost"]:
        ver = p.get("version") or {}
        if not in_win(ver.get("when")):
            continue
        g, sub = classify((p.get("space") or {}).get("key"), [a.get("title") for a in (p.get("ancestors") or [])])
        created = iso(((p.get("history") or {}).get("createdDate")))
        rows.append({"k": "P" if p.get("type") == "page" else "B", "id": p.get("id"), "g": g, "sub": sub,
                     "st": "NEW" if (created and created > ws) else "MOD", "v": ver.get("number"),
                     "at": kst(ver.get("when")), "by": (ver.get("by") or {}).get("displayName", ""),
                     "t": p.get("title"), "msg": (ver.get("message") or "")[:60], "tg": tags(p.get("title"))})
    for x in data["comment"]:
        ver = x.get("version") or {}
        if not in_win(ver.get("when")):
            continue
        ct = x.get("container") or {}
        anc = [a.get("title") for a in (ct.get("ancestors") or [])] + [ct.get("title") or ""]
        g, sub = classify((x.get("space") or {}).get("key"), anc)
        rows.append({"k": "C", "id": ct.get("id"), "g": g, "sub": sub, "st": "CMT", "v": ver.get("number"),
                     "at": kst(ver.get("when")), "by": (ver.get("by") or {}).get("displayName", ""),
                     "t": ct.get("title") or "", "msg": "", "tg": tags(ct.get("title") or "")})
    for a in data["attachment"]:
        ver = a.get("version") or {}
        if not in_win(ver.get("when")):
            continue
        ct = a.get("container") or {}
        if IMAGE_RE.search(a.get("title") or ""):
            img_count += 1
            key = ct.get("title") or "?"
            img_by[key] = img_by.get(key, 0) + 1
            continue
        anc = [q.get("title") for q in (ct.get("ancestors") or [])] + [ct.get("title") or ""]
        g, sub = classify((a.get("space") or {}).get("key"), anc)
        rows.append({"k": "A", "id": ct.get("id"), "g": g, "sub": sub,
                     "st": "NEW" if ver.get("number") == 1 else "MOD", "v": ver.get("number"),
                     "at": kst(ver.get("when")), "by": (ver.get("by") or {}).get("displayName", ""),
                     "t": "{} @ {}".format(a.get("title"), ct.get("title") or ""), "msg": "",
                     "tg": tags(ct.get("title") or "")})

    rows.sort(key=lambda r: r["at"] or "", reverse=True)  # 같은 그룹 안에서는 최근 순
    rows.sort(key=lambda r: (ORDER.index(r["g"]) if r["g"] in ORDER else len(ORDER),
                             0 if r["st"] == "NEW" else 1))
    stats = {"window": [args.start, args.end], "raw": raw, "rows": len(rows),
             "imgExcluded": img_count, "byGroup": {}}
    for r in rows:
        s = stats["byGroup"].setdefault(r["g"], {"NEW": 0, "MOD": 0, "CMT": 0, "total": 0})
        s[r["st"]] += 1
        s["total"] += 1
    lines = ["#STATS " + json.dumps(stats, ensure_ascii=False)]
    for i, r in enumerate(rows, 1):
        lines.append("|".join(esc(v) for v in [i, r["k"], r["id"], r["g"], r["sub"], r["st"], r["v"],
                                               r["at"], r["by"], r["t"], r["msg"], r["tg"]]))
    lines += [f"IMG|{esc(k)}|{v}" for k, v in img_by.items()]
    emit("\n".join(lines), args.out)
    return 0


# --------------------------------------------------------------------------- 정독
def content(site, pid, ver=None):
    q = f"?status=historical&version={ver}&" if ver else "?"
    j, _ = site.get(f"/rest/api/content/{urllib.parse.quote(str(pid))}{q}expand=body.view,version")
    if "__error" in j:
        raise RuntimeError(j["__error"][:150])
    return j


def base_version(site, pid, ws):
    """구간 시작 시각 이전의 마지막 버전 번호 (없으면 None = 구간 내 신규)."""
    for start in range(0, 2000, 50):
        j, _ = site.get(f"/rest/experimental/content/{urllib.parse.quote(str(pid))}/version?limit=50&start={start}")
        if "__error" in j:
            raise RuntimeError(j["__error"][:150])
        res = j.get("results") or []
        for v in res:
            w = iso(v.get("when"))
            if w and w <= ws:
                return v.get("number")
        if len(res) < 50:
            return None
    return None


def cmd_read(args):
    site = Site("ECM")
    ws = iso(args.start)
    if not ws:
        raise SystemExit("ERROR: --start 가 ISO UTC 형식이 아니다")
    with open(args.jobs, "r", encoding="utf-8-sig") as f:
        jobs = json.load(f)
    out = []
    for job in jobs:
        pid, mode = job["id"], job.get("mode", "body")
        try:
            cur = content(site, pid)
            cur_lines = to_text(((cur.get("body") or {}).get("view") or {}).get("value")).split("\n")
            cur_v = (cur.get("version") or {}).get("number")
            head = f"=== {pid} | {cur.get('title')} | v{cur_v}"
            base = base_version(site, pid, ws) if mode == "diff" else None
            if mode == "diff" and base and base != cur_v:
                prev_lines = to_text(((content(site, pid, base).get("body") or {}).get("view") or {})
                                     .get("value")).split("\n")
                ps, cs = set(prev_lines), set(cur_lines)
                add = ["+ " + l for l in cur_lines if l not in ps]
                dele = ["- " + l for l in prev_lines if l not in cs]
                head += f" | diff v{base}→v{cur_v}"
                text = "\n".join(add + dele) if (add or dele) else "(텍스트 변화 없음 — 서식·첨부만 변경)"
            else:
                if mode == "diff":
                    head += " | 구간 내 신규 → 본문"
                text = "\n".join(cur_lines)
            body = text[:args.max] + ("\n…(이하 생략)" if len(text) > args.max else "")
            out.append(f"{head}\n{body}")
        except Exception as e:
            out.append(f"=== {pid} | ERROR {e}")
    emit("\n\n".join(out), args.out)
    return 0


def cmd_check(args):
    site = Site("ECM")
    j, code = site.get("/rest/api/user/current")
    if "__error" in j or j.get("type") != "known":
        print(f"ECM_CHECK FAIL ({site.source}) : {j.get('__error') or ('type=' + str(j.get('type')))}")
        if code in (401, 403):
            print("토큰이 만료·무효이거나 권한이 없다 → 재발급, 또는 크롬 폴백으로 진행한다.")
        return 1
    print(f"ECM_CHECK OK ({site.source}) : {j.get('displayName')} / {j.get('username')} / {site.url}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="eCoDY-ECM 일일 변경 수집·정독 (PAT, 읽기 전용)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="토큰 확인 (/rest/api/user/current)")
    c = sub.add_parser("collect", help="구간 내 변경 수집 → #STATS + 행 목록")
    c.add_argument("--start", required=True, help="WINDOW_START (ISO UTC)")
    c.add_argument("--end", required=True, help="WINDOW_END (ISO UTC)")
    c.add_argument("--out")
    r = sub.add_parser("read", help="본문(body) 또는 구간 시작 버전과의 변경(diff)")
    r.add_argument("--start", required=True, help="WINDOW_START (ISO UTC, diff 기준)")
    r.add_argument("--jobs", required=True, help='[{"id","mode"}] JSON 파일')
    r.add_argument("--max", type=int, default=2500)
    r.add_argument("--out")
    a = ap.parse_args()
    return {"check": cmd_check, "collect": cmd_collect, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
