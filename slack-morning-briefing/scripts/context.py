#!/usr/bin/env python3
"""아침 브리핑 실행 컨텍스트 · 커버리지 원장 · 발송 게이트.

산문 규칙은 실행마다 해석이 흔들리지만 exit code 와 JSON 원장은 흔들리지 않는다.
날짜 방어가 유일하게 작동해온 이유가 `date` 셸 호출이라는 기계 근거였으므로,
같은 원리를 수집 커버리지에도 적용한다.

사용법
  context.py now
  context.py init  --window-start <unix초> [--sources sources.json]
  context.py mark  --source <id> --count <n>
  context.py add   --source <id> --label <표시명> [--discovered]
  context.py gate-coverage
  context.py gate-final --header "<헤더 첫 줄>" --collected N --adopted N --dropped N
  context.py status
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DOW_KO = {1: "월", 2: "화", 3: "수", 4: "목", 5: "금", 6: "토", 7: "일"}

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
WORK_ROOT = os.environ.get("BRIEFING_WORKDIR", "/tmp/slack-morning-briefing")


# ---------------------------------------------------------------- 시각

def now_ctx():
    n = dt.datetime.now(KST)
    iso = n.strftime("%Y-%m-%d")
    dow_num = n.isoweekday()
    return {
        "TODAY": iso,
        "DOW_NUM": dow_num,
        "TODAY_DOW": DOW_KO[dow_num],
        "NOW_KST": n.strftime("%H:%M"),
        "NOW_EPOCH": int(n.timestamp()),
    }


def dow_of(date_str):
    """YYYY-MM-DD -> 한글 요일. 형식이 틀리면 None."""
    try:
        d = dt.date.fromisoformat(date_str)
    except ValueError:
        return None
    return DOW_KO[d.isoweekday()]


# ---------------------------------------------------------------- 원장

def ledger_path():
    return os.path.join(WORK_ROOT, now_ctx()["TODAY"], "ledger.json")


def load_ledger():
    p = ledger_path()
    if not os.path.exists(p):
        sys.exit(f"[FAIL] 원장이 없습니다: {p}\n  -> context.py init 을 먼저 실행하세요 (P2).")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_ledger(led):
    p = ledger_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=2)


def cmd_init(args):
    src_path = args.sources or os.path.join(SKILL_DIR, "sources.json")
    with open(src_path, encoding="utf-8") as f:
        src = json.load(f)

    entries = {}
    for ch in src.get("channels", []):
        entries[ch["id"]] = {
            "kind": "channel",
            "label": ("🔒" if ch.get("private") else "#") + ch["name"],
            "tier": ch.get("tier", "core"),
            "status": "pending",
            "count": None,
        }
    for dm in src.get("dm_roster", []):
        entries[dm["id"]] = {
            "kind": "dm",
            "label": f"{dm['name']}({dm.get('name_en', '')})".replace("()", ""),
            "tier": "core",
            "status": "pending",
            "count": None,
        }
    entries["dm_sweep"] = {
        "kind": "sweep",
        "label": "DM 전체 검색 (to:me)",
        "tier": "core",
        "status": "pending",
        "count": None,
    }
    entries["discovery_sweep"] = {
        "kind": "sweep",
        "label": "발견 스윕 (미등록 소스 검출)",
        "tier": "core",
        "status": "pending",
        "count": None,
    }

    led = {
        "created_at": now_ctx(),
        "window_start": args.window_start,
        "sources": entries,
    }
    save_ledger(led)
    out = dict(now_ctx())
    out["window_start"] = args.window_start
    out["ledger"] = ledger_path()
    out["pending"] = len(entries)
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_add(args):
    led = load_ledger()
    led["sources"][args.source] = {
        "kind": "channel",
        "label": args.label,
        "tier": "discovered" if args.discovered else "core",
        "status": "pending",
        "count": None,
    }
    save_ledger(led)
    print(f"[ADD] {args.source} ({args.label}) -> pending")


RESOLVED = ("swept", "unavailable")


def cmd_mark(args):
    led = load_ledger()
    if args.source not in led["sources"]:
        sys.exit(f"[FAIL] 원장에 없는 소스입니다: {args.source}\n"
                 f"  -> 발견된 신규 소스라면 context.py add 로 먼저 등록하세요.")
    s = led["sources"][args.source]
    s["status"] = args.status
    s["count"] = args.count
    if args.reason:
        s["reason"] = args.reason
    save_ledger(led)
    pend = [k for k, v in led["sources"].items() if v["status"] not in RESOLVED]
    if args.status == "unavailable":
        print(f"[WARN] {args.source} unavailable ({args.reason or '사유 미기재'}) "
              f"· 남은 pending {len(pend)}\n"
              f"  -> 게이트는 통과시키되 감사 푸터에 반드시 표시하세요.")
    else:
        print(f"[OK] {args.source} swept ({args.count}건) · 남은 pending {len(pend)}")


def cmd_status(args):
    led = load_ledger()
    for sid, s in led["sources"].items():
        flag = "✔" if s["status"] == "swept" else "…"
        cnt = "-" if s["count"] is None else s["count"]
        print(f" {flag} {sid:<24} {s['label']:<40} {cnt}")


# ---------------------------------------------------------------- 게이트

def cmd_gate_coverage(args):
    led = load_ledger()
    pend = [(k, v) for k, v in led["sources"].items() if v["status"] not in RESOLVED]
    if pend:
        print("[FAIL] 게이트#1 커버리지 — 소인되지 않은 소스가 남았습니다:")
        for k, v in pend:
            print(f"   · {k}  {v['label']}")
        print("\n  -> P3 으로 돌아가 전부 소인한 뒤 다시 실행하세요. 진행 금지.")
        print("     소스가 오류(channel_not_found 등)로 읽히지 않으면 포기하지 말고")
        print("     mark --status unavailable --reason <사유> 로 명시 처리하세요.")
        sys.exit(1)
    total = sum(v["count"] or 0 for v in led["sources"].values())
    ch = sum(1 for v in led["sources"].values() if v["kind"] == "channel")
    dm = sum(1 for v in led["sources"].values() if v["kind"] == "dm")
    una = [(k, v) for k, v in led["sources"].items() if v["status"] == "unavailable"]
    print(f"[PASS] 게이트#1 커버리지 — 소스 {len(led['sources'])}개 해소 "
          f"(채널 {ch} / DM {dm}) · 수집 {total}건")
    if una:
        print(f"[WARN] 접근 불가 소스 {len(una)}개 — 감사 푸터에 표시하세요:")
        for k, v in una:
            print(f"   · {k}  {v['label']}  ({v.get('reason', '사유 미기재')})")


def cmd_gate_final(args):
    ctx = now_ctx()
    fails = []

    # 1) 헤더 날짜 == TODAY
    m = re.search(r"(\d{4}-\d{2}-\d{2})", args.header)
    if not m:
        fails.append("헤더에서 YYYY-MM-DD 를 찾지 못했습니다.")
    else:
        hdr_date = m.group(1)
        if hdr_date != ctx["TODAY"]:
            fails.append(f"헤더 날짜 {hdr_date} != 오늘 {ctx['TODAY']} (하루 밀림)")

    # 2) 헤더에 요일 표기가 있으면 일치해야
    dm_ = re.search(r"\(([월화수목금토일])\)", args.header)
    if dm_ and dm_.group(1) != ctx["TODAY_DOW"]:
        fails.append(f"헤더 요일 ({dm_.group(1)}) != 오늘 요일 ({ctx['TODAY_DOW']})")

    # 3) TODAY 로부터 재계산한 요일 == TODAY_DOW (획득값 무결성)
    if dow_of(ctx["TODAY"]) != ctx["TODAY_DOW"]:
        fails.append("TODAY 와 TODAY_DOW 가 내부 모순입니다. 시계를 다시 읽으세요.")

    # 4) 커버리지
    unavailable = []
    try:
        led = load_ledger()
        pend = [k for k, v in led["sources"].items() if v["status"] not in RESOLVED]
        if pend:
            fails.append(f"소인되지 않은 소스 {len(pend)}개: {', '.join(pend)}")
        unavailable = [(k, v) for k, v in led["sources"].items()
                       if v["status"] == "unavailable"]
    except SystemExit:
        fails.append("원장이 없습니다. 수집을 수행하지 않았습니다.")

    # 4b) 접근 불가 소스는 푸터에 표시했어야 한다
    if unavailable and "접근 불가" not in args.header and not args.ack_unavailable:
        fails.append(f"접근 불가 소스 {len(unavailable)}개가 있는데 푸터/헤더에 "
                     f"표시되지 않았습니다. 표시했다면 --ack-unavailable 을 붙이세요.")

    # 5) 회계
    if args.collected != args.adopted + args.dropped:
        fails.append(f"회계 불일치: 수집 {args.collected} != 채택 {args.adopted} "
                     f"+ 제외 {args.dropped} (누수 "
                     f"{args.collected - args.adopted - args.dropped}건)")

    if fails:
        print("[FAIL] 게이트#2 — 발송 금지")
        for f in fails:
            print(f"   · {f}")
        print("\n  -> 헤더는 부분 수정하지 말고 references/format.md 골격으로 "
              "처음부터 다시 만드세요.")
        sys.exit(1)

    tail = f" · 접근 불가 {len(unavailable)}" if unavailable else ""
    print(f"[PASS] 게이트#2 — {ctx['TODAY']}({ctx['TODAY_DOW']}) "
          f"· 수집 {args.collected} = 채택 {args.adopted} + 제외 {args.dropped} "
          f"· 커버리지 완전{tail}. 발송 가능.")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("now")

    p = sub.add_parser("init")
    p.add_argument("--window-start", required=True)
    p.add_argument("--sources")

    p = sub.add_parser("mark")
    p.add_argument("--source", required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--status", choices=["swept", "unavailable"], default="swept")
    p.add_argument("--reason", help="unavailable 일 때의 사유 (not_found / no_access / error)")

    p = sub.add_parser("add")
    p.add_argument("--source", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--discovered", action="store_true")

    sub.add_parser("gate-coverage")
    sub.add_parser("status")

    p = sub.add_parser("gate-final")
    p.add_argument("--header", required=True)
    p.add_argument("--collected", type=int, required=True)
    p.add_argument("--adopted", type=int, required=True)
    p.add_argument("--dropped", type=int, required=True)
    p.add_argument("--ack-unavailable", action="store_true",
                   help="접근 불가 소스를 푸터에 표시했음을 확인")

    a = ap.parse_args()
    if a.cmd == "now":
        print(json.dumps(now_ctx(), ensure_ascii=False, indent=2))
    elif a.cmd == "init":
        cmd_init(a)
    elif a.cmd == "mark":
        cmd_mark(a)
    elif a.cmd == "add":
        cmd_add(a)
    elif a.cmd == "gate-coverage":
        cmd_gate_coverage(a)
    elif a.cmd == "gate-final":
        cmd_gate_final(a)
    elif a.cmd == "status":
        cmd_status(a)


if __name__ == "__main__":
    main()
