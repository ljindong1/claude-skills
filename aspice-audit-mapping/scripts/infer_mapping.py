"""키워드 사전 기반 절차그룹·산출물 추론 (설계서 v0.3 — 결정론 1차).

모드 B(B2)와 모드 A UNCLAIMED 그룹 추정(§4.2 ⑤c)이 공용으로 사용한다.
사전 정본: assets/oii_map.json 의 keyword_dict (하나만 유지).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from config import INFERRED_HIGH, INFERRED_LOW, UNCLASSIFIED


@dataclass(frozen=True, slots=True)
class Inference:
    """파일 1건의 추론 결과."""

    level: str  # INFERRED_HIGH | INFERRED_LOW | UNCLASSIFIED
    procedure_group: str | None
    work_product: str | None
    pam: str | None
    basis: str | None


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def infer_from_path(relpath: str, keyword_dict: list[dict[str, Any]]) -> Inference:
    """파일명 + 상위 폴더 경로명으로 키워드 사전을 대조한다."""
    haystack = normalize_text(relpath.replace("\\", "/"))
    hits: list[tuple[dict[str, Any], str]] = []
    for entry in keyword_dict:
        matched_keyword = next(
            (kw for kw in entry["keywords"] if normalize_text(kw) in haystack), None
        )
        if matched_keyword is not None:
            hits.append((entry, matched_keyword))

    if not hits:
        return Inference(UNCLASSIFIED, None, None, None, None)

    groups = {entry["procedure_group"] for entry, _ in hits}
    if len(groups) == 1:
        entry, keyword = hits[0]
        return Inference(
            INFERRED_HIGH, entry["procedure_group"], entry["work_product"],
            entry.get("pam"), f"파일명·경로 키워드 '{keyword}'",
        )
    # 복수 그룹 후보 → LOW (첫 후보를 대표로 제시하되 AI 확인 대상)
    entry, keyword = hits[0]
    others = ", ".join(sorted(groups))
    return Inference(
        INFERRED_LOW, entry["procedure_group"], entry["work_product"],
        entry.get("pam"), f"키워드 '{keyword}' 외 복수 그룹 후보({others}) — AI 확인 대상",
    )
