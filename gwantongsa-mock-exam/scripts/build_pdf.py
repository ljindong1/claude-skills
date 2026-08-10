#!/usr/bin/env python3
"""관통사 모의고사 PDF 생성 스크립트 (문제지 + 해설지).

사용법:
    python3 build_pdf.py exam.json 출력디렉토리

출력:
    출력디렉토리/관통사_모의고사_{회차}_문제지.pdf
    출력디렉토리/관통사_모의고사_{회차}_해설지.pdf

인쇄 규격: A4, 2단 구성, 본문 8pt, 여백 최소(6mm) — 종이 절약형.
의존성: weasyprint (pip install weasyprint --break-system-packages),
        Noto Sans CJK KR 폰트(컨테이너에 기본 설치됨).
"""
import json
import sys
import html
from pathlib import Path

CIRCLED = "①②③④"

CSS = """
@page {
    size: A4;
    margin: 6mm 7mm 8mm 7mm;
    @bottom-center { content: counter(page) " / " counter(pages); font-size: 6pt; color: #888; }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Noto Sans CJK KR', sans-serif; font-size: 8pt; line-height: 1.4; color: #111; }
.header { border: 1.2pt solid #222; margin-bottom: 5pt; width: 100%; border-collapse: collapse; }
.header td { padding: 4pt 6pt; vertical-align: middle; border: none; }
.header .title { font-size: 11pt; font-weight: bold; }
.header .meta { font-size: 7pt; text-align: right; color: #333; }
.namebox { font-size: 7.5pt; border-top: 0.4pt solid #999; margin-top: 2pt; padding-top: 2pt; }
.columns { column-count: 2; column-gap: 6mm; column-rule: 0.3pt solid #bbb; column-fill: auto; }
.subject-band { background: #222; color: #fff; font-weight: bold; font-size: 9pt; padding: 2pt 5pt; margin: 3pt 0 4pt 0; break-inside: avoid; }
.q { break-inside: avoid; margin-bottom: 6pt; }
.q .stem { font-weight: bold; margin-bottom: 2pt; }
.q .stem .qno { display: inline-block; min-width: 14pt; }
.passage { border: 0.5pt solid #555; padding: 3pt 4pt; margin: 2pt 0 3pt 0; font-size: 7.5pt; background: #f7f7f7; white-space: pre-wrap; }
.choices { margin-left: 2pt; }
.choices div { margin-bottom: 0.5pt; }
.anskey { break-inside: avoid; margin-bottom: 6pt; }
.anskey table { border-collapse: collapse; width: 100%; font-size: 7.5pt; text-align: center; }
.anskey td, .anskey th { border: 0.4pt solid #666; padding: 1.5pt 0; }
.anskey th { background: #eee; }
.exp { break-inside: avoid; margin-bottom: 5pt; }
.exp .head { font-weight: bold; }
.exp .ans { color: #000; background: #e8e8e8; padding: 0 3pt; }
.exp .body { margin-top: 1pt; }
.exp .wrong { margin-top: 1pt; color: #333; font-size: 7.5pt; }
"""


def esc(t):
    return html.escape(str(t or ""))


def question_html(q):
    parts = [f'<div class="q"><div class="stem"><span class="qno">{q["no"]}.</span> {esc(q["question"])}</div>']
    if q.get("passage"):
        parts.append(f'<div class="passage">{esc(q["passage"])}</div>')
    parts.append('<div class="choices">')
    for i, c in enumerate(q["choices"]):
        parts.append(f"<div>{CIRCLED[i]} {esc(c)}</div>")
    parts.append("</div></div>")
    return "".join(parts)


def answer_table_html(subject):
    qs = subject["questions"]
    rows = []
    for start in range(0, len(qs), 13):
        chunk = qs[start:start + 13]
        rows.append("<tr>" + "".join(f"<th>{q['no']}</th>" for q in chunk) + "</tr>")
        rows.append("<tr>" + "".join(f"<td>{CIRCLED[q['answer'] - 1]}</td>" for q in chunk) + "</tr>")
    return f'<div class="anskey"><table>{"".join(rows)}</table></div>'


def explanation_html(q):
    parts = [
        f'<div class="exp"><div class="head">{q["no"]}. <span class="ans">정답 {CIRCLED[q["answer"] - 1]}</span></div>',
        f'<div class="body">{esc(q["explanation"])}</div>',
    ]
    wrong = q.get("wrong") or []
    if wrong:
        items = " ".join(esc(w) for w in wrong)
        parts.append(f'<div class="wrong">[오답 풀이] {items}</div>')
    parts.append("</div>")
    return "".join(parts)


def build(exam, out_dir):
    from weasyprint import HTML

    title = exam.get("title", "관광통역안내사 모의고사")
    date = exam.get("date", "")
    round_no = exam.get("round", "")
    label = f"제{round_no}회" if round_no else ""

    # ---- 문제지 ----
    body = [f'<table class="header"><tr><td><div class="title">{esc(title)} {label}</div>'
            f'<div class="namebox">성명: ____________&nbsp;&nbsp;점수: ______ / 50</div></td>'
            f'<td class="meta">{esc(date)}<br>국사(1~25) · 관광자원해설(26~50)<br>4지선다 · 시험시간 50분</td></tr></table>',
            '<div class="columns">']
    for s in exam["subjects"]:
        body.append(f'<div class="subject-band">{esc(s["name"])}</div>')
        for q in s["questions"]:
            body.append(question_html(q))
    body.append("</div>")
    exam_html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(body)}</body></html>"

    # ---- 해설지 ----
    # 주의: 정답표를 포함한 모든 내용을 2단 컬럼 흐름 '안'에 배치한다.
    # 전폭(full-width) 대형 테이블이 첫 페이지에 단독으로 놓이면 일부 PDF 미리보기
    # 뷰어가 1페이지 렌더링에 실패하는 사례가 있어, 문제지와 동일한 구조로 통일한다.
    body = [f'<table class="header"><tr><td><div class="title">{esc(title)} {label} — 정답 및 해설</div></td>'
            f'<td class="meta">{esc(date)}</td></tr></table>',
            '<div class="columns">']
    for s in exam["subjects"]:
        body.append(f'<div class="subject-band">{esc(s["name"])} 정답표</div>')
        body.append(answer_table_html(s))
    for s in exam["subjects"]:
        body.append(f'<div class="subject-band">{esc(s["name"])} 해설</div>')
        for q in s["questions"]:
            body.append(explanation_html(q))
    body.append("</div>")
    ans_html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(body)}</body></html>"

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"_{round_no}회" if round_no else ""
    exam_pdf = out / f"관통사_모의고사{suffix}_문제지.pdf"
    ans_pdf = out / f"관통사_모의고사{suffix}_해설지.pdf"
    HTML(string=exam_html).write_pdf(str(exam_pdf))
    HTML(string=ans_html).write_pdf(str(ans_pdf))
    # 인쇄용 HTML도 함께 저장 (Google Drive 업로드용 — 브라우저에서 열어 인쇄하면 PDF와 동일한 레이아웃)
    exam_htm = out / f"관통사_모의고사{suffix}_문제지.html"
    ans_htm = out / f"관통사_모의고사{suffix}_해설지.html"
    exam_htm.write_text(exam_html, encoding="utf-8")
    ans_htm.write_text(ans_html, encoding="utf-8")
    print(f"OK: {exam_pdf}")
    print(f"OK: {ans_pdf}")
    print(f"OK: {exam_htm}")
    print(f"OK: {ans_htm}")
    return exam_pdf, ans_pdf


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        exam = json.load(f)
    build(exam, sys.argv[2])
