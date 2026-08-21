"""aspice-audit-mapping 공용 상수 정의 (설계서 v0.4 기준).

경로·프로젝트명 등 실행별 값은 CLI 인자로 받는다 — 이 모듈에 하드코딩하지 않는다.
"""

from __future__ import annotations

import re
from typing import Final

SCHEMA_VERSION: Final[str] = "1.3.0"
SKILL_NAME: Final[str] = "aspice-audit-mapping"
SKILL_VERSION: Final[str] = "0.5.0"

# ── 모드 ─────────────────────────────────────────────────────────
MODE_CHECKLIST: Final[str] = "checklist"
MODE_FOLDER: Final[str] = "folder_inferred"

# ── evidence 상태 6종 (references/matching_rules.md 정본) ────────
STATUS_MATCHED: Final[str] = "MATCHED"
STATUS_VERSION_MISMATCH: Final[str] = "VERSION_MISMATCH"
STATUS_MISSING: Final[str] = "MISSING"
STATUS_SYSTEM_URL: Final[str] = "SYSTEM_URL"
STATUS_EXCLUDED: Final[str] = "EXCLUDED"
STATUS_PARTIAL: Final[str] = "PARTIAL"
STATUS_SUSPECT: Final[str] = "SUSPECT"      # v0.3: 불일치 증거 있음
STATUS_UNVERIFIED: Final[str] = "UNVERIFIED"  # v0.4: 확인 불가 (불일치 단정 금지)

ITEM_STATUSES: Final[tuple[str, ...]] = (
    STATUS_MATCHED, STATUS_VERSION_MISMATCH, STATUS_MISSING,
    STATUS_SYSTEM_URL, STATUS_EXCLUDED, STATUS_PARTIAL,
    STATUS_SUSPECT, STATUS_UNVERIFIED,
)

AI_ASSESSMENT_REQUIRED: Final[tuple[str, ...]] = (
    STATUS_MISSING, STATUS_VERSION_MISMATCH, STATUS_SYSTEM_URL,
    STATUS_PARTIAL, STATUS_SUSPECT, STATUS_UNVERIFIED,
)

# ── 매칭 근거 (v0.2) ────────────────────────────────────────────
MATCH_EXACT: Final[str] = "exact"
MATCH_NORMALIZED: Final[str] = "normalized"
MATCH_FUZZY_AI: Final[str] = "fuzzy_ai"

# ── 무결성 코드 (v0.3 §4.2 ③′) ─────────────────────────────────
INTEGRITY_OK: Final[str] = "OK"
INTEGRITY_EMPTY: Final[str] = "FILE_EMPTY"
INTEGRITY_CORRUPT: Final[str] = "FILE_CORRUPT"
INTEGRITY_FORMAT: Final[str] = "FORMAT_MISMATCH"
INTEGRITY_PASSWORD: Final[str] = "PASSWORD_PROTECTED"
INTEGRITY_NOT_CHECKED: Final[str] = "NOT_CHECKED"  # 구현 노트: 파일 미접근(listing 모드) — 경고 대상
INTEGRITY_CODES: Final[tuple[str, ...]] = (
    INTEGRITY_OK, INTEGRITY_EMPTY, INTEGRITY_CORRUPT,
    INTEGRITY_FORMAT, INTEGRITY_PASSWORD, INTEGRITY_NOT_CHECKED,
)
# v0.4 이분류 (설계서 §4.2 ③′): [결함 증거] → SUSPECT / [확인 불가] → UNVERIFIED
INTEGRITY_DEFECT_CODES: Final[tuple[str, ...]] = (
    INTEGRITY_EMPTY, INTEGRITY_CORRUPT, INTEGRITY_FORMAT,
)
INTEGRITY_UNVERIFIABLE_CODES: Final[tuple[str, ...]] = (
    INTEGRITY_PASSWORD, INTEGRITY_NOT_CHECKED,
)

# ── 정체성 확인 어휘 (v0.3 §4.2 ⑤b) ────────────────────────────
IDENTITY_MATCH: Final[str] = "일치"
IDENTITY_MISMATCH: Final[str] = "불일치"
IDENTITY_UNDECIDABLE: Final[str] = "판단 불가"
IDENTITY_RESULTS: Final[tuple[str, ...]] = (
    IDENTITY_MATCH, IDENTITY_MISMATCH, IDENTITY_UNDECIDABLE,
)

# ── UNCLAIMED link_reason (v0.3 §4.2 ③) ────────────────────────
LINK_NOT_LISTED: Final[str] = "NOT_LISTED"
LINK_VERSION_SUPERSEDED: Final[str] = "VERSION_SUPERSEDED"
LINK_REJECTED_CANDIDATE: Final[str] = "REJECTED_CANDIDATE"
LINK_REASONS: Final[tuple[str, ...]] = (
    LINK_NOT_LISTED, LINK_VERSION_SUPERSEDED, LINK_REJECTED_CANDIDATE,
)

# ── 모드 B 추론 수준 (v0.3 §4.3) ────────────────────────────────
INFERRED_HIGH: Final[str] = "INFERRED_HIGH"
INFERRED_LOW: Final[str] = "INFERRED_LOW"
UNCLASSIFIED: Final[str] = "UNCLASSIFIED"
INFERENCE_LEVELS: Final[tuple[str, ...]] = (INFERRED_HIGH, INFERRED_LOW, UNCLASSIFIED)

# ── 입력 검증 오류 코드 (v0.3 §4.1 — 정본: references/output_contract.md) ──
FATAL: Final[str] = "FATAL"
PAUSE: Final[str] = "PAUSE"
WARN: Final[str] = "WARN"

# ── 스캔 제외·문서 분류 ─────────────────────────────────────────
EXCLUDED_FILE_PATTERNS: Final[tuple[str, ...]] = ("~$", ".tmp", "Thumbs.db")
EXCLUDED_FILE_SUFFIXES: Final[tuple[str, ...]] = (".lnk",)
EXCLUDED_DIR_PREFIXES: Final[tuple[str, ...]] = ("_", ".")

DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = (
    ".doc", ".docx", ".xls", ".xlsx", ".xlsm", ".ppt", ".pptx",
    ".pdf", ".hwp", ".md", ".txt", ".csv", ".eml",
)

KNOWN_EXTENSIONS: Final[tuple[str, ...]] = (
    ".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".pptx", ".ppt",
    ".pdf", ".zip", ".eml", ".csv", ".txt", ".md", ".hwp",
)

VERSION_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:[_\-\s(]|^)(v\d+(?:\.\d+)*|rev\s?\d+|r\d{1,3}|\d{6})(?:[_\-\s)]|$)",
    re.IGNORECASE,
)

# ── Target 시트 파싱 ────────────────────────────────────────────
HEADER_NO: Final[str] = "No."
HEADER_WORK_PRODUCT: Final[str] = "출력 작업 산출물"
HEADER_GROUP_HINT: Final[str] = "프로세스"
HEADER_FILE_HINT: Final[str] = "파일"
HEADER_REMARK_HINT: Final[str] = "비고"
HEADER_NOTE_HINT: Final[str] = "note"
SHEET_PREFIX: Final[str] = "Target"
GUIDE_ROW_MARK: Final[str] = "<작성 지침>"
TARGET_MARK: Final[str] = "점검 대상"
NON_TARGET_MARK: Final[str] = "미대상"

# ── AI 초안 마커 (모드 B §4.3-6) ────────────────────────────────
DRAFT_META_SHEET: Final[str] = "_ai_draft_meta"

FUZZY_THRESHOLD: Final[float] = 0.60
