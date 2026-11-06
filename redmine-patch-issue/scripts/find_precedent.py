#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ASEC 프로젝트의 패치 일감 선례를 모은다 - 양식과 필드값을 얻기 위해서다.

내용을 베끼기 위한 것이 아니다. references/tracing.md 4절을 보라:
같은 패치의 일감은 다른 사람이 먼저 해 둔 것이어도 답지이고, 베끼면 그 사람이
빠뜨린 것까지 물려받는다. 여기서 얻을 것은 제목 꼴, 본문 절 구성, 사용자정의
필드에 실제로 쓰이는 값, 직전 회차 번호, 적용 건 일감 번호다.

    python find_precedent.py --controller TPMS
    python find_precedent.py --controller PSU --version 2.1.10
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT = "mobilgene-classic-mobase-asec"
HERE = os.path.dirname(os.path.abspath(__file__))
REDMINE = os.path.normpath(os.path.join(HERE, "..", "..", "redmine-issue",
                                        "scripts", "redmine.py"))

# ASEC 의 두 꼴. 추적은 둘 다 Task 다 - Delivery_Patch 는 제목 규칙이다.
RE_ROUND = re.compile(r"Delivery_Patch", re.I)
RE_UMBRELLA = re.compile(r"SWP\s*모듈\s*패치\s*적용", re.I)
RE_VER = re.compile(r"\[V\.?([0-9][0-9.]*)\]")


def run_json(args):
    if not os.path.exists(REDMINE):
        sys.exit("redmine.py 를 찾을 수 없습니다: %s" % REDMINE)
    cmd = [sys.executable, REDMINE] + args + ["--json"]
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode != 0:
        sys.stderr.write(p.stderr.decode("utf-8", "replace"))
        sys.exit("redmine.py 실패 (종료코드 %d)" % p.returncode)
    try:
        return json.loads(out)
    except ValueError:
        sys.exit("JSON 파싱 실패:\n%s" % out[:800])


def cf(issue, name):
    for f in issue.get("custom_fields") or []:
        if f.get("name") == name:
            v = f.get("value")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            return (v or "").strip()
    return ""


def main():
    ap = argparse.ArgumentParser(description="ASEC 패치 일감 선례 조회")
    ap.add_argument("--controller", default="",
                    help="제어기/차종 키워드 (예: TPMS, PSU). 비우면 전체")
    ap.add_argument("--version", default="",
                    help="이번 회차 버전. 같은 회차 일감이 이미 있으면 경고한다")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", help="JSON 저장 경로")
    a = ap.parse_args()

    data = run_json(["search", "--project", PROJECT, "--status", "*",
                     "--limit", str(a.limit)])
    issues = data.get("issues") or []

    kw = a.controller.lower()
    rounds = []
    umbrellas = []
    for it in issues:
        subj = it.get("subject") or ""
        if kw and kw not in subj.lower():
            continue
        if RE_ROUND.search(subj):
            rounds.append(it)
        elif RE_UMBRELLA.search(subj):
            umbrellas.append(it)

    def line(it):
        return "  #%-6s %-10s %-14s %s" % (
            it.get("id"),
            (it.get("status") or {}).get("name", "")[:10],
            (it.get("author") or {}).get("name", "")[:14],
            (it.get("subject") or "").strip())

    o = []
    o.append("ASEC(%s) 일감 %d건 중 키워드 '%s' 로 거름"
             % (PROJECT, len(issues), a.controller or "(전체)"))

    o.append("")
    o.append("[회차 일감 - 제목에 Delivery_Patch] %d건" % len(rounds))
    for it in rounds:
        o.append(line(it))
    if not rounds:
        o.append("  없음 - 이 제어기의 첫 회차다. 제목 꼴은 다른 제어기 선례를 보라")

    o.append("")
    o.append("[적용 건 일감 - SWP 모듈 패치 적용 건] %d건" % len(umbrellas))
    for it in umbrellas:
        o.append(line(it))
    if not umbrellas:
        o.append("  없음 - 적용 건 일감을 만들지 사용자에게 물어라 (issue-forms.md 3절)")

    # 사용자정의 필드 분포 - 회차 일감만. 양식의 근거는 같은 성격의 일감이어야 한다.
    fields = ["일감검토자", "일감완료자", "SWP 계열(공용화)", "SWP 계열 버전", "차량단계"]
    pool = rounds or [it for it in issues if RE_ROUND.search(it.get("subject") or "")]
    o.append("")
    o.append("[사용자정의 필드 분포 - 회차 일감 %d건 기준]" % len(pool))
    dist = {}
    for name in fields:
        c = {}
        for it in pool:
            v = cf(it, name)
            if v:
                c[v] = c.get(v, 0) + 1
        dist[name] = c
        o.append("  %s" % name)
        if not c:
            o.append("      (기입된 것이 없다 - 추측하지 말고 물어라)")
        for v, n in sorted(c.items(), key=lambda kv: -kv[1]):
            o.append("      %2d회  %s" % (n, v))

    # 중복 경고 - ASEC 에 같은 회차가 이미 있으면 새로 만들지 않는다
    dup = []
    if a.version:
        for it in rounds:
            if a.version in (it.get("subject") or ""):
                dup.append(it)
    if dup:
        o.append("")
        o.append("[중복 경고] ASEC 에 같은 버전의 회차 일감이 이미 있다. "
                 "새로 만들지 말고 수정/코멘트를 제안하라")
        for it in dup:
            o.append(line(it))
            auth = (it.get("author") or {}).get("name", "")
            o.append("      등록자 %s - 내가 아니면 직접 고치지 않는다(코멘트 초안만)" % auth)

    # 직전 회차 추정 - 버전 문자열 기준
    if rounds:
        def vkey(it):
            m = RE_VER.findall(it.get("subject") or "")
            return tuple(int(x) for x in m[0].split(".")) if m else ()
        ordered = sorted([it for it in rounds if vkey(it)], key=vkey)
        if ordered:
            o.append("")
            o.append("[버전 순 회차] 직전 적용 건을 본문 1절 목적에 적는다")
            for it in ordered:
                o.append(line(it))

    print("\n".join(o))

    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as f:
            json.dump({"project": PROJECT, "controller": a.controller,
                       "rounds": rounds, "umbrellas": umbrellas,
                       "field_distribution": dist, "duplicates": dup},
                      f, ensure_ascii=False, indent=2)
        print("")
        print("JSON : %s" % a.out)


if __name__ == "__main__":
    main()
