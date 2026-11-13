"""정본에 새 차종을 추가한다 (기준 차종 + 블록도·기능사양표 규칙으로 O/X 초안).

  1. 기준 차종(like)이 속한 시트마다 새 차종을 기준 차종 바로 오른쪽 열로 넣는다 (차종시트).
  2. 그 시트의 항목마다 값을 정한다.
     - 기준 차종 값이 O/X 이고 규칙 결과가 O 또는 X 이면 → 규칙 결과 (근거: 규칙)
     - 그 밖 (규칙 판단 불가·조건부 O?, 판단 기준 없음, 기준 차종 값이 O/X 가 아님) → 기준 차종 값 (근거: 기준 차종, 확인 필요)
  3. 정본 '차종별값' 격자에 새 차종 열을 기준 차종 바로 오른쪽에 넣고 값을 채운다 (적용예외에는 넣지 않는다 —
     적용예외는 담당자가 확인한 예외만 둔다). 예전 구조 정본이면 이때 새 구조로 바꿔 저장한다.
  4. 차종 행, 개정이력 '차종 추가' 행을 더한다.
결과로 확인 목록(행마다 시트·항목·값·근거·규칙 근거)을 돌려준다. 담당자는 '확인 필요' 행부터 보면 된다.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from .projects import ProjectRegistry
from .master_grid import GRID, clean, drop_default_column, vehicle_order, write_exceptions, write_grid
from .rawdata import load
from .rules import evaluate, parse_rule


def _ox(v: str) -> str | None:
    s = str(v or "").strip().upper()
    return s[0] if s[:1] in ("O", "X") else None


_clean = clean          # 보이지 않는 공백을 걷어 낸 값 — 'O\xa0' 와 'O' 를 같은 값으로 본다


def _set(ws, r: int, c: int, v) -> None:
    cell = ws.cell(r, c)
    if v is None or v == "":
        return
    if isinstance(v, int):
        cell.value = v
    else:
        cell.value, cell.data_type, cell.number_format = str(v), "s", "@"


def _append(ws, row: dict) -> None:
    head = [c.value for c in ws[1]]
    r = ws.max_row + 1
    while r > 2 and all(ws.cell(r - 1, j + 1).value in (None, "") for j in range(len(head))):
        r -= 1                                          # 끝의 빈 행 위로
    for j, h in enumerate(head, 1):
        _set(ws, r, j, row.get(h))


def plan_vehicle(master: Path, name: str, like: str, fs: dict, bd: dict, reg: ProjectRegistry,
                 code: str | None = None) -> dict:
    """정본은 고치지 않고 추가 계획(값·근거)만 만든다."""
    raw = load(master)
    code = code or reg.code_for(name, "diagspec")
    if code in raw.project_codes:
        raise ValueError(f"이미 정본에 있는 차종입니다: {code}")
    if like not in raw.project_codes:
        raise ValueError(f"기준 차종이 정본에 없습니다: {like}")
    signals = {e["project"]: set(e["signals"]) for e in bd["by_project"]}
    variants = {e["project"]: {k: set(v) for k, v in e["variants"].items()} for e in bd["by_project"]}
    feats: dict[str, dict[str, bool]] = {}
    for f in fs["features"]:
        for proj, regions in f["applicability"].items():
            feats.setdefault(proj, {})[f["name"].upper()] = any(v["state"] in ("STD", "OPT", "VAL") for v in regions.values())
    sheets = [s for s in raw.sheets if like in raw.sheet_vehicles(s)]
    rows = []
    for s in sheets:
        for it in raw.items_of(s):
            base = _clean(raw.value(it, like))
            rule = parse_rule(it.get("적용 판단 기준", ""), it.get("Tool 표시", ""))
            res, why = evaluate(rule, code, signals, feats, variants) if rule.get("evaluable") else (None, rule.get("reason", ""))
            if _ox(base) and res in ("O", "X"):
                val, src = res, "규칙"
            else:
                val = base
                if not str(it.get("적용 판단 기준", "")).strip():
                    src = "기준 차종 (판단 기준 없음)"
                elif not _ox(base):
                    src = "기준 차종 (O/X 아닌 값)"
                else:
                    src = "기준 차종 — 확인 필요"
            rows.append({"시트": s, "항목ID": it["항목ID"], "코드": it.get("코드", ""), "이름": str(it.get("이름", "")).split("\n")[0],
                         "값": val, "기준 차종 값": base, "근거": src, "규칙 결과": res or "", "규칙 근거": why,
                         "적용 판단 기준": it.get("적용 판단 기준", ""),
                         "Tool 표시": it.get("Tool 표시", "")})
    like_row = next((p for p in raw.projects if p["차종코드"] == like), {})
    return {"code": code, "name": name, "like": like, "sheets": sheets, "rows": rows,
            "like_label": " ".join(str(like_row.get("원본 표기", "")).split(" | ")[0].split()) or like,
            "variants": sorted(variants.get(code, {})),
            "has_blockdiag": code in signals, "has_funcspec": code in feats}


def apply_vehicle(master: Path, out: Path, plan: dict, owner: str = "", rev: str = "", author: str = "",
                  note: str = "") -> Path:
    """계획을 정본에 써서 out 에 저장한다 (입력 정본은 그대로 둔다)."""
    wb = load_workbook(master)
    code, like, today = plan["code"], plan["like"], date.today().isoformat()

    _append(wb["차종"], {"차종코드": code, "원본 표기": plan["name"], "담당자": owner})

    ws = wb["차종시트"]                                  # 기준 차종 바로 오른쪽에 끼우고 뒤 차종을 한 칸씩 민다
    head = [c.value for c in ws[1]]
    ci, si, oi = head.index("차종코드") + 1, head.index("시트") + 1, head.index("열순서") + 1
    like_pos = {}
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, ci).value == like:
            like_pos[ws.cell(r, si).value] = int(ws.cell(r, oi).value or 0)
    for r in range(2, ws.max_row + 1):
        s, o = ws.cell(r, si).value, ws.cell(r, oi).value
        if s in like_pos and o is not None and int(o) > like_pos[s]:
            ws.cell(r, oi).value = int(o) + 1
    for s in plan["sheets"]:
        _append(ws, {"차종코드": code, "시트": s, "열순서": like_pos.get(s, 0) + 1})

    # 차종별값 격자: 정본의 지금 값 + 새 차종 열 (기준 차종 바로 오른쪽)
    raw = load(master)
    member = {sh: set(raw.sheet_vehicles(sh)) for sh in raw.sheets}
    values = {(it["항목ID"], c): raw.value(it, c) or "" for it in raw.items for c in member.get(it["시트"], ())}
    if GRID in wb.sheetnames:
        codes = [str(h) for h in next(wb[GRID].iter_rows(min_row=1, max_row=1, values_only=True))[4:] if h]
    else:                                                # 예전 구조 → 새 구조로 바꿔 저장
        codes = vehicle_order(raw.sheets, raw.membership)
        write_exceptions(wb, [e for e in raw.exception_rows.values() if str(e.get("사유") or "").strip()])
        drop_default_column(wb)
    codes += [c for c in raw.project_codes if c not in codes]
    codes.insert(codes.index(like) + 1 if like in codes else len(codes), code)
    for sh in plan["sheets"]:
        member.setdefault(sh, set()).add(code)
    for row in plan["rows"]:
        values[(row["항목ID"], code)] = row["값"]
    write_grid(wb, raw.items, codes, member, values)

    _append(wb["개정이력"], {"Rev": rev, "날짜": today, "작성자": author or owner, "종류": "차종 추가",
                          "내용": f"{plan['name']} 차종 추가\n↓ 기준 차종 {like} 대비 변경점은 확인 목록 참고" + (f"\n{note}" if note else ""),
                          "차종": plan["name"]})
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def write_checklist(plan: dict, path: Path) -> Path:
    """확인 목록 엑셀: '확인 필요' → 기준 차종과 다른 값 → 나머지 순."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    order = {"기준 차종 — 확인 필요": 0, "규칙": 2}
    rows = sorted(plan["rows"], key=lambda r: (order.get(r["근거"], 1) if not (r["근거"] == "규칙" and r["값"] != r["기준 차종 값"]) else 0.5,
                                               r["시트"], r["항목ID"]))
    cols = ["시트", "코드", "이름", "값", "기준 차종 값", "근거", "규칙 결과", "규칙 근거", "적용 판단 기준", "Tool 표시", "항목ID"]
    wb = Workbook()
    ws = wb.active
    ws.title = "확인 목록"
    ws.append(cols)
    warn, diff = PatternFill("solid", fgColor="FDF4D8"), PatternFill("solid", fgColor="DBEAFE")
    for r in rows:
        ws.append([str(r.get(c, "")) for c in cols])
        fill = warn if "확인 필요" in r["근거"] else diff if r["값"] != r["기준 차종 값"] else None
        if fill:
            for c in ws[ws.max_row]:
                c.fill = fill
    for c in ws[1]:
        c.font = Font(bold=True)
    for letter, w in zip("ABCDEFGHIJK", (22, 10, 36, 6, 10, 22, 8, 36, 40, 30, 22)):
        ws.column_dimensions[letter].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    info = wb.create_sheet("요약")
    n = lambda f: sum(1 for r in plan["rows"] if f(r))
    for k, v in [("차종", f"{plan['name']} ({plan['code']})"), ("기준 차종", plan["like"]), ("시트 수", len(plan["sheets"])),
                 ("항목 수", len(plan["rows"])), ("규칙으로 정한 값", n(lambda r: r["근거"] == "규칙")),
                 ("  그중 기준 차종과 다른 값", n(lambda r: r["근거"] == "규칙" and r["값"] != r["기준 차종 값"])),
                 ("기준 차종 값 — 확인 필요", n(lambda r: "확인 필요" in r["근거"])),
                 ("기준 차종 값 — 판단 기준 없음·O/X 아님", n(lambda r: r["근거"].startswith("기준 차종 (") )),
                 ("블록도", "있음" if plan["has_blockdiag"] else "없음 — 블록도 근거 항목은 모두 기준 차종 값"),
                 ("기능사양표", "있음" if plan["has_funcspec"] else "없음 — 기능사양표 근거 항목은 모두 기준 차종 값")]:
        info.append([k, v])
    info.column_dimensions["A"].width, info.column_dimensions["B"].width = 34, 60
    wb.save(path)
    return path
