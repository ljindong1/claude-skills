"""시트 기재 파일명과 인벤토리를 대조하는 매칭 로직 (references/matching_rules.md 구현).

v0.3: match_basis 기록, 동일 파일명 복수 경로 자동 채택 금지(candidates 나열),
fuzzy 후보 경로 추적(link_reason=REJECTED_CANDIDATE 판별용).
build_mapping.py 가 import 해서 사용한다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from config import (
    FUZZY_THRESHOLD,
    KNOWN_EXTENSIONS,
    MATCH_EXACT,
    MATCH_NORMALIZED,
    STATUS_MATCHED,
    STATUS_MISSING,
    STATUS_SYSTEM_URL,
    STATUS_VERSION_MISMATCH,
    VERSION_TOKEN_RE,
)

_SYMBOL_RE = re.compile(r"[\s_\-\[\]()]+")


@dataclass(frozen=True, slots=True)
class NormalizedName:
    norm: str
    base: str
    version: str | None


@dataclass(slots=True)
class EvidenceResult:
    """엔트리 1건의 매칭 결과 (계약 1.3.0 evidence).

    v0.4: decided_by(확정 주체 — exact/normalized는 "스크립트" 자동 기입,
    fuzzy_ai는 "미확정"으로 시작해 게이트에서 사람이 확정), human_decision
    (사람 정정 내용 — 버전 선택·경로 선택 등의 기록처), carried_over(재매핑
    승계 표시 — §4.4).
    """

    listed: str
    status: str
    match_basis: str | None = None
    decided_by: str | None = None
    human_decision: str | None = None
    carried_over: bool = False
    integrity: str | None = None
    identity: dict[str, object] | None = None
    resolved_path: str | None = None
    resolved_mtime: str | None = None
    resolved_bytes: int | None = None
    version_note: str | None = None
    candidates: list[str] = field(default_factory=list)


def strip_extension(name: str) -> str:
    lowered = name.lower()
    for extension in KNOWN_EXTENSIONS:
        if lowered.endswith(extension):
            return name[: -len(extension)]
    return name


def extract_extension(name: str) -> str | None:
    lowered = name.strip().lower()
    for extension in KNOWN_EXTENSIONS:
        if lowered.endswith(extension):
            return extension
    return None


def normalize(name: str) -> NormalizedName:
    text = unicodedata.normalize("NFC", name.strip())
    text = strip_extension(text)
    versions = [m.group(1) for m in VERSION_TOKEN_RE.finditer(text)]
    version = versions[-1].lower().replace(" ", "") if versions else None
    base_text = VERSION_TOKEN_RE.sub(" ", text)
    return NormalizedName(
        norm=_SYMBOL_RE.sub("", text).lower(),
        base=_SYMBOL_RE.sub("", base_text).lower(),
        version=version,
    )


def bigram_overlap(a: str, b: str) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    bigrams_a = {a[i: i + 2] for i in range(len(a) - 1)}
    bigrams_b = {b[i: i + 2] for i in range(len(b) - 1)}
    union = bigrams_a | bigrams_b
    return len(bigrams_a & bigrams_b) / len(union) if union else 0.0


class InventoryIndex:
    """인벤토리 파일 레코드의 정규화 색인."""

    def __init__(self, files: list[dict[str, object]]) -> None:
        self._records: list[tuple[NormalizedName, str | None, dict[str, object]]] = []
        for record in files:
            name = str(record["name"])
            self._records.append((normalize(name), extract_extension(name), record))
        # link_reason 판별용 추적
        self.fuzzy_candidate_paths: set[str] = set()
        self.matched_bases: set[str] = set()

    def match(self, listed: str) -> EvidenceResult:
        if listed.lower().startswith(("http://", "https://")):
            return EvidenceResult(listed=listed, status=STATUS_SYSTEM_URL)

        target = normalize(listed)
        target_extension = extract_extension(listed)

        for exactness in (MATCH_EXACT, MATCH_NORMALIZED):
            hits: list[tuple[str | None, dict[str, object]]] = []
            for candidate, extension, record in self._records:
                if exactness == MATCH_EXACT:
                    is_hit = str(record["name"]).strip() == listed.strip()
                else:
                    is_hit = (
                        candidate.norm == target.norm
                        or target.norm in candidate.norm
                        or candidate.norm in target.norm
                    )
                if is_hit:
                    hits.append((extension, record))
            if not hits:
                continue
            # 확장자 우선 선별
            if target_extension is not None:
                preferred = [(e, r) for e, r in hits if e == target_extension]
                if preferred:
                    hits = preferred
            # 동일 파일명이 복수 경로 → 자동 채택 금지 (v0.3)
            distinct_paths = {str(r["relpath"]) for _, r in hits}
            if len(distinct_paths) > 1:
                for path in distinct_paths:
                    self.fuzzy_candidate_paths.add(path)
                return EvidenceResult(
                    listed=listed, status=STATUS_MISSING,
                    version_note="동일 파일명 복수 경로 — 자동 채택 금지, AI 제안·게이트 확정 필요",
                    candidates=sorted(distinct_paths),
                )
            record = hits[0][1]
            self.matched_bases.add(normalize(str(record["name"])).base)
            return EvidenceResult(
                listed=listed, status=STATUS_MATCHED, match_basis=exactness,
                decided_by="스크립트",  # v0.4: 결정론 매칭의 주체 표시
                resolved_path=str(record["relpath"]),
                resolved_mtime=record.get("mtime"),  # type: ignore[arg-type]
                resolved_bytes=record.get("size"),  # type: ignore[arg-type]
            )

        # base 일치·버전 상이
        version_hits = [
            (candidate, record)
            for candidate, _extension, record in self._records
            if candidate.base and candidate.base == target.base
        ]
        if version_hits:
            folder_versions = sorted({c.version or "(버전표기없음)" for c, _ in version_hits})
            for _, record in version_hits:
                self.fuzzy_candidate_paths.add(str(record["relpath"]))
            return EvidenceResult(
                listed=listed, status=STATUS_VERSION_MISMATCH,
                version_note=(
                    f"시트 기재 {target.version or '(버전표기없음)'} ↔ "
                    f"폴더 보유 {', '.join(folder_versions)}"
                ),
                candidates=[str(record["relpath"]) for _, record in version_hits],
            )

        # fuzzy 후보 → MISSING + candidates (AI 확정 전 승격 금지)
        fuzzy = sorted(
            (
                (bigram_overlap(target.base, candidate.base), record)
                for candidate, _extension, record in self._records
                if candidate.base
            ),
            key=lambda pair: pair[0], reverse=True,
        )
        candidates = [
            str(record["relpath"]) for score, record in fuzzy[:3] if score >= FUZZY_THRESHOLD
        ]
        for path in candidates:
            self.fuzzy_candidate_paths.add(path)
        return EvidenceResult(listed=listed, status=STATUS_MISSING, candidates=candidates)

    def relpaths(self) -> set[str]:
        return {str(record["relpath"]) for _, _, record in self._records}
