"""IBU 블록도 파서.

입력은 Visio를 PDF로 변환한 파일(Visio 'PDF로 저장' 또는 LibreOffice `soffice --headless --convert-to pdf`).
텍스트 추출은 PyMuPDF(pip 패키지 pymupdf)로 한다 — 별도 프로그램 설치가 필요 없다.
쪽마다 제목에서 차종·SMK/IMMO형을 읽고, 본문 텍스트에서 신호명을 뽑는다.
PDF 텍스트 추출은 도형 안에서 잘린 이름이 생길 수 있어, 두 가지 읽기(위치순 단어 / 기본 순서)의 합집합을 쓰고
'가장 긴 이름의 접두사'로 잘린 이름을 흡수한다. (.vsdx 저장본을 받으면 XML에서 정확히 읽도록 교체 예정)
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from ..core.projects import ProjectRegistry, variant_of

SIG = re.compile(r"\b(?:L|P|A|HS|LS|C|D|B|V)_[A-Za-z0-9]+(?:(?:\([+-]\))?_[A-Za-z0-9]+)*(?:\([+-]\))?")   # V_: 안테나 구동, (+)/(-): 극성 표시
BUS = re.compile(r"\b(?:HS-|FD-|LS-)?(?:B|P|C|G|M)-CAN(?:FD)?\b|\bLIN\s*(?:ch\.?\s*)?\d\b", re.I)
HISTORY_PAT = re.compile(r"^\s*HISTORY\b", re.I)


def _layout_text(pg) -> str:
    """poppler -layout 에 해당: 첫 줄은 위치순 텍스트의 첫 줄(쪽 제목), 그 아래는 단어를 줄별로 공백으로 이은 것.
    위치순 텍스트를 그대로 쓰면 맞붙은 글상자가 한 단어로 붙어(L_WiperPowerRLY_OUTOption) 신호명이 틀어진다."""
    t = pg.get_text("text", sort=True)
    title = next((ln for ln in t.splitlines() if ln.strip()), "")
    title = re.split(r"\s{3,}", title.strip())[0]               # 제목 오른쪽에 떨어져 있는 글상자(▶블록도작성기준 등)는 버린다
    title = re.sub(r"(?<=[^\s(])IBU\(", " IBU(", title)          # '통합IBU(' 처럼 붙어 읽힌 차종명과 IBU 사이를 띄운다
    lines: dict[tuple[int, int], list] = {}
    for x0, _y0, _x1, _y1, w, b, ln, _n in pg.get_text("words", sort=True):
        lines.setdefault((b, ln), []).append((x0, w))
    body = "\n".join(" ".join(w for _, w in sorted(v)) for _, v in sorted(lines.items()))
    return title + "\n" + body


def _raw_text(pg) -> str:
    """poppler -raw 에 해당: PDF 안에 들어 있는 순서 그대로."""
    return pg.get_text("text")


def _absorb_truncated(names: set[str]) -> set[str]:
    """'L_KeyHoleILL_OU'처럼 잘린 이름이 더 긴 이름의 접두사이면 긴 쪽으로 합친다."""
    full = sorted(names, key=len, reverse=True)
    keep = set()
    for n in full:
        if any(k != n and k.startswith(n) and len(k) - len(n) <= 4 for k in keep):
            continue
        keep.add(n)
    return keep


def parse_blockdiag(pdf: Path, reg: ProjectRegistry) -> dict:
    doc = pymupdf.open(str(pdf))
    pages, history = [], []
    for p in range(1, doc.page_count + 1):
        t_layout = _layout_text(doc[p - 1])
        t_raw = _raw_text(doc[p - 1])
        title = next((ln.strip() for ln in t_layout.splitlines() if ln.strip()), "")
        if HISTORY_PAT.match(title) or "HISTORY" in t_layout[:400].upper():
            history.append({"page": p, "text": t_layout[:4000]})
            continue
        sigs = set(SIG.findall(t_layout)) | set(SIG.findall(t_raw))
        sigs = {s for s in sigs if len(s) > 5 and not s.endswith("_")}
        sigs = _absorb_truncated(sigs)
        buses = sorted({b.upper().replace(" ", "") for b in BUS.findall(t_layout)})
        proj_raw = re.sub(r"\s*IBU\s*\(.*$", "", title).strip(" _")
        pages.append({
            "page": p, "title": title, "project": reg.code_for(proj_raw, "blockdiag"),
            "project_raw": proj_raw, "variant": variant_of(title),
            "signals": sorted(sigs), "buses": buses,
        })
    # 차종별 신호 존재(SMK/IMMO 합집합 + 변형별 보존)
    by_proj: dict[str, dict] = {}
    for pg in pages:
        e = by_proj.setdefault(pg["project"], {"project": pg["project"], "variants": {}, "signals": set(), "pages": []})
        e["variants"].setdefault(pg["variant"] or "UNK", set()).update(pg["signals"])   # 같은 형이 여러 쪽이면 합집합
        e["signals"].update(pg["signals"])
        e["pages"].append(pg["page"])
    for e in by_proj.values():
        e["signals"] = sorted(e["signals"])
        e["variants"] = {k: sorted(v) for k, v in e["variants"].items()}
    all_sigs = sorted({s for pg in pages for s in pg["signals"]})
    return {"file": pdf.name, "pages": pages, "history_pages": [h["page"] for h in history],
            "by_project": list(by_proj.values()), "signals": all_sigs}
