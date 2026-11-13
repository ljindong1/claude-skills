"""새 차종 추가 보고서 (단일 HTML) — 날짜 폴더에 정본 사본·뷰어·원본양식과 함께 둔다.

무엇을 추가했나 · 근거 자료 · 요약 숫자 · 기준 차종과 다르게 정한 값 · 확인이 필요한 칸(시트별) · 새 차종 불일치 · 다음 할 일.
상세(전 항목)는 같은 폴더의 확인 목록 엑셀에 있다.
"""
from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def humanize(why: str) -> str:
    """규칙 근거 코드 → 담당자가 읽는 말."""
    if not why:
        return ""
    out = []
    for part in why.split(";"):
        p = part.strip()
        if not p:
            continue
        m = re.match(r"signals(?:\[(\w+)\])?:(.*)", p)
        if m:
            form = {"IMMO": "IMMO형(-SMK) ", "SMK": "SMK형 ", "NON_SMK_NON_IMMO": "-SMK·-IMMO형 "}.get(m.group(1) or "", "")
            marks = [x for x in m.group(2).split(",") if x]
            if any(x.startswith("no_") for x in marks):
                out.append(f"{form}블록도 쪽이 없음")
                continue
            have = sum(1 for x in marks if x.startswith("1"))
            txt = f"{form}블록도에 신호 " + ("있음" if have and len(marks) == 1 else "없음" if not have else f"{len(marks)}개 중 {have}개 있음")
            if "1?" in marks:
                txt += " (지역 조건은 판단 불가)"
            if "or?" in marks:
                txt += " (다른 대안 조건은 판단 불가)"
            out.append(txt)
            continue
        if p.startswith("features:"):
            vals = p.split(":", 1)[1].split(",")
            out.append("기능사양표 " + ("적용" if "True" in vals else "미적용" if "False" in vals else "해당 행 없음"))
        elif p.startswith("feature_unmatched:"):
            out.append(f"기능사양표에 '{p.split(':', 1)[1]}' 행 없음")
        elif p == "no_blockdiag":
            out.append("블록도 없음")
        elif p == "no_funcspec":
            out.append("기능사양표 없음")
        elif p.startswith("조건부:"):
            out.append("판단 불가 조건: " + p.split(":", 1)[1])
        else:
            out.append({"free_text": "판단 기준이 자유 문장", "no_criteria": "판단 기준 없음", "standard": "STD(항상 적용)",
                        "unused": "미사용", "bus_only": "버스 조건만 있음"}.get(p, p))
    return " · ".join(dict.fromkeys(out))           # 같은 이유가 여러 조건에서 나오면 한 번만


CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1f2933;--mute:#5f6b7a;--line:#dfe3e8;--accent:#0e7490;--warn-bg:#fdf4d8;--warn:#8a5a00;
--diff-bg:#dbeafe;--diff:#1e40af;--bad-bg:#fde2e1;--bad:#a61b1b;--ok-bg:#dcf2e3;--ok:#1d6b3a}
@media (prefers-color-scheme:dark){:root{--bg:#14181d;--card:#1c2229;--ink:#e6e9ed;--mute:#9aa5b1;--line:#2d3640;--accent:#38bdf8;
--warn-bg:#3a2f12;--warn:#f5c96b;--diff-bg:#1e2c4a;--diff:#9cc2ff;--bad-bg:#4a1f1f;--bad:#ff9d9d;--ok-bg:#183a26;--ok:#8fe0ad}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px;
padding-bottom:6px;border-bottom:2px solid var(--line)}.sub{color:var(--mute);margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.meta{display:grid;grid-template-columns:140px 1fr;gap:6px 14px}.meta dt{color:var(--mute)}.meta dd{margin:0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.kpi .n{font-size:24px;font-weight:700}
.kpi .l{color:var(--mute);font-size:12.5px}.kpi.warn{background:var(--warn-bg)}.kpi.warn .n{color:var(--warn)}
.kpi.diff{background:var(--diff-bg)}.kpi.diff .n{color:var(--diff)}.kpi.bad{background:var(--bad-bg)}.kpi.bad .n{color:var(--bad)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);font-size:13px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--bg);font-weight:600}
td.v,th.v{text-align:center;font-weight:700;width:68px;white-space:nowrap}.note{color:var(--mute);font-size:12.5px}details{margin:8px 0}
summary{cursor:pointer;font-weight:600;padding:6px 0}.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px}
.tag.ok{background:var(--ok-bg);color:var(--ok)}.tag.no{background:var(--warn-bg);color:var(--warn)}ol{margin:6px 0 0 18px;padding:0}
@media print{body{background:#fff}details{display:block}details>summary{list-style:none}}
@media (max-width:640px){.meta{grid-template-columns:1fr}.meta dt{font-weight:600}}
"""


def write_report(plan: dict, path: Path, meta: dict) -> Path:
    """meta: owner, rev, master_copy, viewer, legacy, checklist, attachments[], variants[], new_mismatch[] (dict 행)."""
    e = html.escape
    rows = plan["rows"]
    n = lambda f: sum(1 for r in rows if f(r))
    by_rule = n(lambda r: r["근거"] == "규칙")
    differs = [r for r in rows if r["근거"] == "규칙" and r["값"] != r["기준 차종 값"]]
    check = [r for r in rows if "확인 필요" in r["근거"]]
    copied = n(lambda r: r["근거"].startswith("기준 차종 ("))
    mm = meta.get("new_mismatch") or []
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    variants = meta.get("variants") or []
    bd_txt = ("있음 — " + "·".join({"SMK": "SMK형", "IMMO": "IMMO형"}.get(v, v) for v in variants) + " 쪽"
              if plan["has_blockdiag"] else "없음 — 블록도로 판단하는 항목은 기준 차종 값")
    fs_txt = "있음" if plan["has_funcspec"] else "없음 — 기능사양표로 판단하는 항목은 기준 차종 값"

    def tag(ok):
        return '<span class="tag ok">있음</span>' if ok else '<span class="tag no">없음</span>'

    h = [f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         f"<title>신규 차종 추가 보고 {e(plan['name'])} ({now[:10]})</title><style>{CSS}</style></head><body><main>",
         f"<h1>신규 차종 추가 보고 — {e(plan['name'])}</h1>",
         f"<p class='sub'>{e(meta.get('rev') or '')}{' · ' if meta.get('rev') else ''}{now} 생성 · IBU/BCM 진단사양서</p>",
         "<h2>무엇을 추가했나</h2><div class='card'><dl class='meta'>",
         f"<dt>새 차종</dt><dd><b>{e(plan['name'])}</b> (코드 {e(plan['code'])})</dd>",
         f"<dt>기준 차종</dt><dd>{e(plan.get('like_label') or plan['like'])} (코드 {e(plan['like'])}) — 시트 구성과, 규칙으로 정할 수 없는 값을 이 차종에서 가져옴</dd>",
         f"<dt>담당자</dt><dd>{e(meta.get('owner') or '(미기재)')}</dd>",
         f"<dt>개정 번호</dt><dd>{e(meta.get('rev') or '(미기재)')}</dd>",
         f"<dt>들어간 시트</dt><dd>{len(plan['sheets'])}개 시트, {len(rows)}개 항목</dd>",
         f"<dt>정본</dt><dd>{e(meta.get('master_copy', ''))} (새 차종이 들어간 정본 사본)</dd>",
         "</dl></div>",
         "<h2>근거 자료</h2><div class='card'><dl class='meta'>",
         f"<dt>블록도</dt><dd>{tag(plan['has_blockdiag'])} {e(bd_txt)}</dd>",
         f"<dt>기능사양표</dt><dd>{tag(plan['has_funcspec'])} {e(fs_txt)}</dd>",
         f"<dt>첨부 자료</dt><dd>{e(', '.join(meta.get('attachments') or []) or '없음 (스킬 내장 참조 데이터만 사용)')}</dd>",
         "</dl></div>",
         "<h2>요약</h2><div class='kpis'>",
         f"<div class='card kpi'><div class='n'>{len(rows)}</div><div class='l'>전체 항목</div></div>",
         f"<div class='card kpi'><div class='n'>{by_rule}</div><div class='l'>블록도·기능사양표 규칙으로 정한 값</div></div>",
         f"<div class='card kpi diff'><div class='n'>{len(differs)}</div><div class='l'>그중 기준 차종과 다른 값</div></div>",
         f"<div class='card kpi warn'><div class='n'>{len(check)}</div><div class='l'>기준 차종 값을 넣어 확인이 필요한 칸</div></div>",
         f"<div class='card kpi'><div class='n'>{copied}</div><div class='l'>판단 기준이 없어 기준 차종 값을 쓴 칸</div></div>",
         f"<div class='card kpi {'bad' if mm else ''}'><div class='n'>{len(mm)}</div><div class='l'>새 차종 불일치</div></div>",
         "</div>"]
    if not plan["has_blockdiag"] and not plan["has_funcspec"]:
        h.append("<p class='note'>블록도와 기능사양표가 모두 없어 거의 모든 값이 기준 차종을 그대로 복사한 것입니다.</p>")

    h.append("<h2>기준 차종과 다르게 정한 값</h2>")
    if differs:
        h.append("<table><tr><th>시트</th><th>코드</th><th>항목</th><th class='v'>기준</th><th class='v'>새 차종</th><th>근거</th></tr>")
        for r in differs:
            h.append(f"<tr><td>{e(r['시트'])}</td><td>{e(str(r['코드']))}</td><td>{e(r['이름'])}</td><td class='v'>{e(r['기준 차종 값'])}</td>"
                     f"<td class='v'>{e(r['값'])}</td><td>{e(humanize(r['규칙 근거']))}</td></tr>")
        h.append("</table>")
    else:
        h.append("<p>없음 — 규칙으로 정한 값이 모두 기준 차종과 같습니다.</p>")

    h.append("<h2>확인이 필요한 칸</h2><p class='note'>규칙으로 판단할 수 없어 기준 차종 값을 넣은 칸입니다. "
             "맞지 않으면 정본 '차종별값' 시트에서 고쳐 주세요.</p>")
    if check:
        by_sheet = defaultdict(list)
        for r in check:
            by_sheet[r["시트"]].append(r)
        for sheet, lst in by_sheet.items():
            h.append(f"<details open><summary>{e(sheet)} — {len(lst)}칸</summary><table><tr><th>코드</th><th>항목</th>"
                     "<th class='v'>넣은 값</th><th>판단할 수 없었던 이유</th><th>적용 판단 기준</th></tr>")
            for r in lst:
                h.append(f"<tr><td>{e(str(r['코드']))}</td><td>{e(r['이름'])}</td><td class='v'>{e(r['값'] or '(빈칸)')}</td>"
                         f"<td>{e(humanize(r['규칙 근거']))}</td><td class='note'>{e(str(r['적용 판단 기준']).replace(chr(10), ' / ')[:120])}</td></tr>")
            h.append("</table></details>")
    else:
        h.append("<p>없음</p>")

    h.append("<h2>새 차종 불일치</h2>")
    if mm:
        h.append("<table><tr><th>시트</th><th>코드</th><th>항목</th><th class='v'>정본</th><th class='v'>규칙</th><th>근거</th></tr>")
        for r in mm:
            h.append(f"<tr><td>{e(r['sheet'])}</td><td>{e(r['code'])}</td><td>{e(r['name'].splitlines()[0])}</td>"
                     f"<td class='v'>{e(r['recorded'])}</td><td class='v'>{e(r['rule'])}</td><td>{e(humanize(r['why']))}</td></tr>")
        h.append("</table>")
    else:
        h.append("<p>없음</p>")

    h += ["<h2>다음 할 일</h2><div class='card'><ol>",
          f"<li>위 '확인이 필요한 칸' {len(check)}칸을 검토하고, 고칠 값은 정본 '차종별값'에서 고칩니다.</li>",
          "<li>'기준 차종과 다르게 정한 값'이 실제 사양과 맞는지 확인합니다.</li>"]
    if not plan["has_funcspec"] or not plan["has_blockdiag"]:
        h.append("<li>이 차종의 " + " · ".join(x for x, ok in (("블록도", plan["has_blockdiag"]), ("기능사양표", plan["has_funcspec"])) if not ok)
                 + "를 받으면 다시 추가해 규칙 판단 범위를 넓힙니다.</li>")
    h += ["<li>검토가 끝난 정본을 저장 폴더의 Master로 바꾸고, 뷰어 HTML을 배포합니다.</li></ol></div>",
          f"<p class='note' style='margin-top:20px'>같은 폴더: {e(meta.get('viewer', ''))} · {e(meta.get('legacy', ''))} · "
          f"{e(meta.get('checklist', ''))} (전 항목 상세)</p></main></body></html>"]
    Path(path).write_text("\n".join(h), encoding="utf-8")
    return Path(path)
