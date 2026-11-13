"""Raw data 워크북(진단사양서 정본) 읽기.

워크북은 한 시트 = 한 테이블이다. 이 모듈은 테이블을 읽어 생성기(뷰어·엑셀 양식)가 쓰는 꼴로 넘긴다.

차종별 값 (항목, 차종):
  1. 그 차종이 차종시트에서 항목의 시트에 속하지 않으면 → 값 없음 (None)
  2. '차종별값' 시트(항목 × 차종 격자)의 그 칸 — 빈 칸은 빈 문자열
'적용예외' 시트는 규칙과 다르지만 담당자가 확인한 칸(사유)만 담는다. 값은 격자에서 읽는다.

예전 구조('차종별값' 시트 없음)도 읽는다: 적용예외에 (항목, 차종) 행이 있으면 그 값, 없으면 진단항목의 '기본 적용'.
예전 구조 정본은 core/master_grid.migrate 로 새 구조로 바꾼다.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

from .master_grid import GRID, clean

BLANK = "(빈칸)"
TABLES = ("차종", "차종시트", "진단항목", "값정의", "항목설명", "적용규칙", "적용예외", "개정이력", "참고문서", "코드표")


def _rows(ws) -> list[dict]:
    it = ws.iter_rows(values_only=True)
    head = [str(h) if h is not None else "" for h in next(it)]
    out = []
    for row in it:
        if all(v is None or str(v) == "" for v in row):
            continue
        out.append({h: ("" if v is None else str(v) if not isinstance(v, int) else v) for h, v in zip(head, row) if h})
    return out


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


@dataclass
class RawData:
    path: Path
    projects: list[dict]
    membership: list[dict]
    items: list[dict]
    values: list[dict]
    descriptions: list[dict]
    rules: list[dict]
    exceptions: dict[tuple[str, str], str]
    exception_rows: dict[tuple[str, str], dict]
    history: list[dict]
    refdocs: list[dict]
    grid: dict[tuple[str, str], str] | None = None       # 새 구조: (항목ID, 차종) → 값
    _members: dict[str, list[str]] = field(default_factory=dict)
    _member_set: dict[str, set] = field(default_factory=dict)

    def __post_init__(self) -> None:
        by_sheet = defaultdict(list)
        for m in self.membership:
            by_sheet[m["시트"]].append((_int(m.get("열순서")) or 10**6, m["차종코드"]))
        self._members = {s: [c for _, c in sorted(v)] for s, v in by_sheet.items()}
        self._member_set = {s: set(v) for s, v in self._members.items()}

    # --- 조회
    @property
    def project_codes(self) -> list[str]:
        return [p["차종코드"] for p in self.projects]

    @property
    def latest_rev(self) -> str:
        """개정이력에서 가장 큰 Rev (R391 등). 없으면 'R?'."""
        import re
        best = None
        for h in self.history:
            m = re.fullmatch(r"R(\d+)(?:\.(\d+))?", str(h.get("Rev", "")).strip())
            if m:
                key = (int(m.group(1)), int(m.group(2) or 0))
                if best is None or key > best[0]:
                    best = (key, m.group(0))
        return best[1] if best else "R?"

    @property
    def sheets(self) -> list[str]:
        """진단항목에 나오는 시트 순서."""
        seen = []
        for it in self.items:
            if it["시트"] not in seen:
                seen.append(it["시트"])
        return seen

    def sheet_vehicles(self, sheet: str) -> list[str]:
        return self._members.get(sheet, [])

    def items_of(self, sheet: str) -> list[dict]:
        return [it for it in self.items if it["시트"] == sheet]

    def value(self, item: dict, code: str) -> str | None:
        if code not in self._member_set.get(item["시트"], ()):
            return None
        if self.grid is not None:
            return self.grid.get((item["항목ID"], code), "")
        v = self.exceptions.get((item["항목ID"], code), item.get("기본 적용", ""))
        return "" if v == BLANK else str(v)

    def exception_rows_of(self, item_id: str) -> dict[str, dict]:
        """항목의 적용예외 행 전체 (차종 → 행: 값·사유·근거·확인자·확인일)."""
        return {c: e for (i, c), e in self.exception_rows.items() if i == item_id}

    def values_of(self, item_id: str) -> list[dict]:
        return [v for v in self.values if v["항목ID"] == item_id]

    def descriptions_of(self, item_id: str) -> list[dict]:
        return sorted((d for d in self.descriptions if d["항목ID"] == item_id), key=lambda d: _int(d.get("순서")) or 0)


def load(path: Path | str) -> RawData:
    path = Path(path)
    wb = load_workbook(path, read_only=True, data_only=True)
    missing = [t for t in TABLES if t not in wb.sheetnames]
    if missing:
        raise ValueError(f"워크북에 테이블 시트가 없습니다: {', '.join(missing)} ({path})")
    T = {t: _rows(wb[t]) for t in TABLES if t != "코드표"}
    grid = None
    if GRID in wb.sheetnames:
        grid = {}
        it = wb[GRID].iter_rows(values_only=True)
        head = [str(h) if h is not None else "" for h in next(it)]
        nfix = head.index("이름") + 1 if "이름" in head else 4
        for row in it:
            if not row or row[0] in (None, ""):
                continue
            for code, v in zip(head[nfix:], row[nfix:]):
                if code and v not in (None, ""):
                    grid[(str(row[0]), code)] = clean(v)
    return RawData(
        path=path,
        projects=T["차종"],
        membership=T["차종시트"],
        items=T["진단항목"],
        values=T["값정의"],
        descriptions=T["항목설명"],
        rules=T["적용규칙"],
        exceptions={(e["항목ID"], e["차종"]): str(e["값"]) for e in T["적용예외"]},
        exception_rows={(e["항목ID"], e["차종"]): e for e in T["적용예외"]},
        history=T["개정이력"],
        refdocs=T["참고문서"],
        grid=grid,
    )
