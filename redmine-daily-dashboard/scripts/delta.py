#!/usr/bin/env python3
"""스냅샷 비교 → 델타 산출. 순수 함수만 두어 collect.py 가 import 해 쓴다.

셸 파이프로 JSON 을 흘리지 않는다 (cp949/BOM 파손). 모든 입출력은 호출부가
utf-8 파일로 처리한다.
"""

from datetime import date, datetime

# 미해결이면서 이 일수 이상 updated_on 무변동이면 '정체'.
# 7일은 검토성 과제(주 1회 진척)에 과민해 오탐이 많아 14일로 둔다.
STALE_DAYS = 14

# due_date 가 오늘부터 이 일수 이내면 '마감 임박'.
DUE_SOON_DAYS = 3


def snapshot_record(issue):
    """스냅샷에 남길 최소 필드. 이 다섯 개만으로 모든 이벤트를 판정한다."""
    return {
        "status": (issue.get("status") or {}).get("name"),
        "done_ratio": issue.get("done_ratio"),
        "updated_on": issue.get("updated_on"),
        "due_date": issue.get("due_date"),
        "closed_on": issue.get("closed_on"),
    }


def build_snapshot(issues):
    return {str(i["id"]): snapshot_record(i) for i in issues}


def _is_closed(issue):
    return bool((issue.get("status") or {}).get("is_closed"))


def _parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _parse_dt(s):
    """Redmine 의 updated_on 은 '2026-09-11T02:13:45Z' 형태."""
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def compute_delta(issues, previous, today=None):
    """오늘의 변화 이벤트 목록.

    previous 가 None 이면 첫 실행(baseline) — 이벤트 없이 baseline 플래그만 켠다.
    '변화 없음'과 '비교 대상 없음'은 다른 상태이므로 구분해서 넘긴다.
    """
    today = today or date.today()

    if previous is None:
        return {"baseline": True, "events": []}

    events = []
    for issue in issues:
        iid = str(issue["id"])
        before = previous.get(iid)
        subject = issue.get("subject", "")

        if before is None:
            events.append({"type": "new", "id": issue["id"], "subject": subject,
                           "detail": (issue.get("status") or {}).get("name", "")})
            continue

        now_status = (issue.get("status") or {}).get("name")
        was_status = before.get("status")

        # 완료 전이는 상태 변경의 특수 경우다. 둘 다 내보내면 같은 건이 두 번 잡힌다.
        if _is_closed(issue) and not before.get("closed_on"):
            events.append({"type": "closed", "id": issue["id"], "subject": subject,
                           "detail": f"{was_status} → {now_status}"})
        elif now_status != was_status:
            events.append({"type": "status", "id": issue["id"], "subject": subject,
                           "detail": f"{was_status} → {now_status}"})
        elif issue.get("updated_on") != before.get("updated_on"):
            bits = []
            if issue.get("done_ratio") != before.get("done_ratio"):
                bits.append(f"진척 {before.get('done_ratio')}% → {issue.get('done_ratio')}%")
            if issue.get("due_date") != before.get("due_date"):
                bits.append(f"마감 {before.get('due_date') or '없음'} → {issue.get('due_date') or '없음'}")
            events.append({"type": "updated", "id": issue["id"], "subject": subject,
                           "detail": " · ".join(bits)})

    # 사라진 id = 담당자 변경 또는 접근 권한 상실. 조용히 없애면 추적이 끊긴다.
    current_ids = {str(i["id"]) for i in issues}
    for iid in previous:
        if iid not in current_ids:
            events.append({"type": "gone", "id": int(iid), "subject": "",
                           "detail": "담당에서 빠졌거나 조회되지 않음"})

    order = {"new": 0, "closed": 1, "status": 2, "updated": 3, "gone": 4}
    events.sort(key=lambda e: (order.get(e["type"], 9), e["id"]))
    return {"baseline": False, "events": events}


def compute_attention(issues, today=None):
    """마감 초과 · 마감 임박 · 정체. 미해결 건만 대상."""
    today = today or date.today()
    overdue, due_soon, stale = [], [], []

    for issue in issues:
        if _is_closed(issue):
            continue

        due = _parse_date(issue.get("due_date"))
        if due:
            gap = (due - today).days
            if gap < 0:
                overdue.append({"id": issue["id"], "subject": issue.get("subject", ""),
                                "due_date": issue.get("due_date"), "days": gap})
            elif gap <= DUE_SOON_DAYS:
                due_soon.append({"id": issue["id"], "subject": issue.get("subject", ""),
                                 "due_date": issue.get("due_date"), "days": gap})

        upd = _parse_dt(issue.get("updated_on"))
        if upd:
            idle = (today - upd.date()).days
            if idle >= STALE_DAYS:
                stale.append({"id": issue["id"], "subject": issue.get("subject", ""),
                              "days": idle, "updated_on": issue.get("updated_on")})

    overdue.sort(key=lambda x: x["days"])
    due_soon.sort(key=lambda x: x["days"])
    stale.sort(key=lambda x: -x["days"])
    return {"overdue": overdue, "due_soon": due_soon, "stale": stale}


def recent_closed(issues, days=7, today=None):
    """최근 N일 내 완료된 건."""
    today = today or date.today()
    out = []
    for issue in issues:
        if not _is_closed(issue):
            continue
        closed = _parse_dt(issue.get("closed_on")) or _parse_dt(issue.get("updated_on"))
        if closed and (today - closed.date()).days <= days:
            out.append(issue)
    out.sort(key=lambda i: i.get("closed_on") or i.get("updated_on") or "", reverse=True)
    return out


def open_issues(issues):
    return [i for i in issues if not _is_closed(i)]
