#!/usr/bin/env python3
"""수집 결과 → Confluence HTML 조각.

여기까지가 결정적(deterministic) 영역이다. 숫자와 표는 전부 이 파일이 만들고,
Claude 는 state/commentary.json 에 해설 문장만 얹는다 — Claude 가 표나 건수를
직접 쓰면 지어낼 여지가 생긴다.

단독 실행도 가능하다 (P4 해설을 붙인 뒤 재렌더링):
    python scripts/render.py
"""

import html
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delta as D

# 윈도우 콘솔 기본 인코딩(cp949)은 한글·물결표를 못 찍어 출력이 깨진다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REDMINE_ISSUE_URL = "http://ccm.mobaseelec.com:8080/issues/{id}"

# 표 전체 폭 760px 기준 배분. 합계를 바꾸면 각 셀 값을 전부 같이 고쳐야 한다.
COLS = [52, 190, 96, 60, 64, 56, 112, 52, 78]
HEADERS = ["#", "제목", "프로젝트", "추적", "상태", "우선도", "시작~마감", "진척", "최근갱신"]

# Redmine 상태명 → Confluence status lozenge 색. 미등록 상태는 neutral.
STATUS_COLOR = {
    "신규": "blue", "New": "blue",
    "진행": "yellow", "진행중": "yellow", "In Progress": "yellow",
    "해결": "green", "Resolved": "green",
    "완료": "green", "종료": "green", "Closed": "green",
    "피드백": "purple", "Feedback": "purple",
    "보류": "neutral", "On Hold": "neutral",
    "거절": "red", "Rejected": "red",
}

EVENT_LABEL = {
    "new": "신규 할당",
    "closed": "완료",
    "status": "상태 변경",
    "updated": "갱신",
    "gone": "담당 해제",
}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=False)


def issue_link(iid):
    return f'<a href="{REDMINE_ISSUE_URL.format(id=iid)}">#{iid}</a>'


def status_color(name):
    """이 Redmine 은 상태명을 '신규(new)' 처럼 한/영 병기로 쓴다. 정확히 일치하는
    키가 없으므로 부분 일치로 찾고, 그래도 없으면 neutral."""
    raw = (name or "").strip()
    if raw in STATUS_COLOR:
        return STATUS_COLOR[raw]
    lowered = raw.lower()
    for key, color in STATUS_COLOR.items():
        if key.lower() in lowered:
            return color
    return "neutral"


def status_chip(name):
    return f'<span data-type="status" data-color="{status_color(name)}">{esc(name)}</span>'


def _cell(tag, width, inner):
    return f'<{tag} data-colwidth="{width}"><p>{inner}</p></{tag}>'


def issue_table(issues):
    head = "".join(_cell("th", w, f"<strong>{esc(h)}</strong>")
                   for w, h in zip(COLS, HEADERS))
    rows = []
    for i in issues:
        # 한쪽만 있으면 '2026-09-11~' 처럼 물결을 남겨 어느 쪽이 빈지 보이게 한다.
        start, due = i.get("start_date"), i.get("due_date")
        span = f"{start or ''}~{due or ''}" if (start or due) else "—"
        cells = [
            issue_link(i["id"]),
            esc(i.get("subject")),
            esc((i.get("project") or {}).get("name")),
            esc((i.get("tracker") or {}).get("name")),
            status_chip((i.get("status") or {}).get("name")),
            esc((i.get("priority") or {}).get("name")),
            esc(span),
            f'{i.get("done_ratio", 0)}%',
            esc((i.get("updated_on") or "")[:10]),
        ]
        rows.append("<tr>" + "".join(_cell("td", w, c) for w, c in zip(COLS, cells)) + "</tr>")

    return (
        '<table data-layout="default" data-display-mode="fixed">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render(data, commentary=None):
    commentary = commentary or {}
    issues = data["issues"]
    dlt = data["delta"]
    att = data["attention"]

    open_list = D.open_issues(issues)
    closed_recent = D.recent_closed(issues)
    due_count = len(att["overdue"]) + len(att["due_soon"])
    change_count = len(dlt["events"])

    out = []

    # ── 일감 현황 (KPI) ─────────────────────────────────────────────
    out.append("<h3>일감 현황</h3>")
    if dlt["baseline"]:
        change_text = "오늘 변화 —건(첫 수집)"
    else:
        change_text = f"오늘 변화 <strong>{change_count}</strong>건"
    out.append(
        f"<p>미해결 <strong>{len(open_list)}</strong>건 · {change_text} · "
        f"마감 임박 <strong>{due_count}</strong>건</p>"
    )

    # ── 오늘의 변화 ────────────────────────────────────────────────
    out.append("<h3>오늘의 변화</h3>")
    if dlt["baseline"]:
        out.append("<p>첫 수집입니다. 비교할 직전 스냅샷이 없어 오늘은 기준선만 저장했습니다.</p>")
    elif not dlt["events"]:
        out.append("<p>변화 없음.</p>")
    else:
        items = []
        for e in dlt["events"]:
            label = EVENT_LABEL.get(e["type"], e["type"])
            line = f'<strong>{esc(label)}</strong> · {issue_link(e["id"])}'
            if e.get("subject"):
                line += f' {esc(e["subject"])}'
            if e.get("detail"):
                line += f' <em>({esc(e["detail"])})</em>'
            note = commentary.get(str(e["id"]))
            if note:
                line += f"<br>{esc(note)}"
            items.append(f"<li>{line}</li>")
        out.append("<ul>" + "".join(items) + "</ul>")

    # ── 미해결 일감 ────────────────────────────────────────────────
    out.append("<h3>미해결 일감</h3>")
    if open_list:
        out.append(issue_table(open_list))
    else:
        out.append("<p>미해결 일감이 없습니다.</p>")

    # ── 주의가 필요한 건 (해당 없으면 섹션 자체를 생략) ──────────────
    if att["overdue"] or att["due_soon"] or att["stale"]:
        out.append("<h3>주의가 필요한 건</h3>")
        items = []
        for x in att["overdue"]:
            items.append(
                f'<li><strong>마감 초과</strong> · {issue_link(x["id"])} {esc(x["subject"])} '
                f'— <time datetime="{x["due_date"]}">{x["due_date"]}</time> 기준 {abs(x["days"])}일 경과</li>'
            )
        for x in att["due_soon"]:
            when = "오늘" if x["days"] == 0 else f'D-{x["days"]}'
            items.append(
                f'<li><strong>마감 임박</strong> · {issue_link(x["id"])} {esc(x["subject"])} '
                f'— <time datetime="{x["due_date"]}">{x["due_date"]}</time> ({when})</li>'
            )
        for x in att["stale"]:
            items.append(
                f'<li><strong>정체</strong> · {issue_link(x["id"])} {esc(x["subject"])} '
                f'— {x["days"]}일째 갱신 없음</li>'
            )
        out.append("<ul>" + "".join(items) + "</ul>")

    # ── 최근 완료 (7일) ────────────────────────────────────────────
    if closed_recent:
        rows = "".join(
            f'<li>{issue_link(i["id"])} {esc(i.get("subject"))} '
            f'— {esc((i.get("closed_on") or i.get("updated_on") or "")[:10])}</li>'
            for i in closed_recent
        )
        out.append(
            f"<details><summary>최근 완료 ({len(closed_recent)}건 · 7일)</summary>"
            f"<ul>{rows}</ul></details>"
        )

    stamp = data.get("generated_at") or datetime.now().strftime("%Y-%m-%d %H:%M")
    out.append(f"<blockquote><p>마지막 갱신: {esc(stamp)} · 자동 생성</p></blockquote>")

    return "".join(out)


def main():
    home = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    state = home / "state"

    data_file = state / "latest-data.json"
    if not data_file.exists():
        print(f"[ERROR] {data_file} 이 없습니다. collect.py 를 먼저 실행하세요.", file=sys.stderr)
        return 1

    data = json.loads(data_file.read_text(encoding="utf-8"))

    commentary = {}
    cfile = state / "commentary.json"
    if cfile.exists():
        commentary = json.loads(cfile.read_text(encoding="utf-8"))

    fragment = render(data, commentary)
    out = state / "latest-fragment.html"
    out.write_text(fragment, encoding="utf-8")
    print(f"[OK] 조각 재생성: {out} ({len(fragment)}자, 해설 {len(commentary)}건 반영)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
