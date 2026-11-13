"""통합 뷰어 — 모듈별 뷰어 HTML(BCM, SMK …)을 고친 데 없이 한 파일로 묶고, 맨 위에서 모듈을 전환한다.

각 모듈 뷰어는 페이지 안에 글자 그대로 넣어 두고, 고른 모듈만 iframe(Blob URL)으로 띄운다.
그래서 통합 뷰어의 내용은 고른 판의 모듈별 뷰어와 항상 같다. 같은 폴더에 어떤 판을 묶었는지 적은 구성 기록을 남긴다.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _stamp(viewer_html: str) -> dict:
    """모듈 뷰어 안 데이터의 stats 에서 Rev·생성 일시·정본 이름을 읽는다 (머리글·구성 기록에 쓰려고)."""
    m = re.search(r'"sources":\{[^}]*"diagspec":"([^"]*)"[^}]*\},"rev":"([^"]*)","module":"([^"]*)","built_at":"([^"]*)"', viewer_html)
    if not m:
        return {"rev": "", "built_at": "", "master": ""}
    return {"master": m.group(1), "rev": m.group(2), "built_at": m.group(4)}


SHELL = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{--bg:#f7f8fa;--bar:#ffffff;--ink:#1f2933;--mute:#5f6b7a;--line:#dfe3e8;--accent:#0e7490;--on:#ffffff}
@media (prefers-color-scheme:dark){:root{--bg:#14181d;--bar:#1c2229;--ink:#e6e9ed;--mute:#9aa5b1;--line:#2d3640;--accent:#38bdf8;--on:#0b1116}}
html,body{height:100%;margin:0}body{display:flex;flex-direction:column;background:var(--bg);color:var(--ink);
font:14px/1.4 "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:8px 16px;background:var(--bar);border-bottom:1px solid var(--line)}
header b{font-size:15px}.tabs{display:flex;gap:6px}.tabs button{border:1px solid var(--line);background:transparent;color:var(--ink);
border-radius:8px;padding:6px 14px;font:inherit;font-weight:600;cursor:pointer}.tabs button[aria-selected=true]{background:var(--accent);
color:var(--on);border-color:var(--accent)}.ver{color:var(--mute);font-size:12.5px}iframe{flex:1;width:100%;border:0;background:var(--bg)}
</style></head><body><header><b>IBU 진단사양 통합 뷰어</b><div class="tabs" role="tablist" id="tabs"></div><span class="ver" id="ver"></span></header>
<iframe id="view" title="모듈 뷰어"></iframe>
<script>const PAGES = [];</script>
__BODIES__
<script>
const PARTS = __PARTS__;
const urls = {};
function src(i){ if(!urls[i]){ urls[i]=URL.createObjectURL(new Blob([PAGES[i]],{type:'text/html'})); } return urls[i]; }
function show(i){ document.querySelectorAll('#tabs button').forEach((b,j)=>b.setAttribute('aria-selected', j===i));
  document.getElementById('view').src = src(i); try{ localStorage.setItem('combined-tab', i); }catch(e){} }
const tabs=document.getElementById('tabs');
PARTS.forEach((p,i)=>{ const b=document.createElement('button'); b.role='tab'; b.textContent=p.module; b.title=`${p.module} ${p.rev} · ${p.built_at} 생성`; b.onclick=()=>show(i); tabs.appendChild(b); });
document.getElementById('ver').textContent = PARTS.map(p=>`${p.module} ${p.rev} (${p.date})`).join(' · ') + ' · __BUILT__ 묶음';
let start=0; try{ const s=+localStorage.getItem('combined-tab'); if(s>=0&&s<PARTS.length) start=s; }catch(e){}
show(start);
</script>
</body></html>"""


def build_combined(parts: list[tuple[str, Path]], day: Path, date: str) -> tuple[Path, Path]:
    """parts: [(모듈, 모듈 뷰어 HTML 경로)] → 통합 뷰어 HTML, 구성 기록(.txt)."""
    built = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    meta, bodies = [], []
    for i, (mod, path) in enumerate(parts):
        text = Path(path).read_text(encoding="utf-8")
        st = _stamp(text)
        d = re.search(r"(\d{8})", Path(path).name)
        meta.append({"module": mod, "rev": st["rev"], "built_at": st["built_at"], "master": st["master"],
                     "date": d.group(1) if d else "", "viewer": Path(path).name})
        # JS 문자열로 넣는다: '</' → '<\\/', '<!--' → '<\\!--' 는 JS 안에서 원래 글자로 돌아오고, 바깥 script 태그는 닫히지 않는다
        lit = json.dumps(text, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
        bodies.append(f"<script>PAGES[{i}] = {lit};</script>")
    title = "IBU 진단사양 통합 뷰어 " + " · ".join(f"{m['module']} {m['rev']}" for m in meta)
    page = (SHELL.replace("__TITLE__", html.escape(title))
                 .replace("__PARTS__", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"))
                 .replace("__BUILT__", built)
                 .replace("__BODIES__", "\n".join(bodies)))
    out = day / f"ibu_diagspec_통합뷰어_{date}.html"
    out.write_text(page, encoding="utf-8")
    note = day / f"통합뷰어_구성_{date}.txt"
    note.write_text("통합 뷰어 구성 (" + built + ")\n" + "\n".join(
        f"- {m['module']}: {m['rev']} · {m['date']} 판 · 뷰어 {m['viewer']} · 정본 {m['master']} · {m['built_at']} 생성" for m in meta) + "\n",
        encoding="utf-8")
    return out, note
