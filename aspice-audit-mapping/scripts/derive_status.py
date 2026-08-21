"""item_status 파생·집계·미해결 산출 (설계서 v0.4 §4.2 ④ 우선순위표 — 결정론 정본).

build_mapping.py(초기 파생)·validate_mapping.py(정합 검사)가 공용으로 import 하고,
⑤ AI 단계(identity 기입) 이후의 재파생은 CLI로 수행한다:

  python derive_status.py mapping.json          # item_status·summary·gate.unresolved 재계산 후 덮어씀
  python derive_status.py mapping.json --check  # 재계산 결과와 현재 값의 차이만 출력 (수정 없음)

파생 우선순위표(첫 일치 규칙 적용 — references/matching_rules.md 정본):

  0. target=false                                  → EXCLUDED
  1. evidence 중 [결함 증거] 존재                   → SUSPECT
     (identity "불일치" / FILE_EMPTY / FILE_CORRUPT / FORMAT_MISMATCH)
  2. (1 아님) [확인 불가] 존재                      → UNVERIFIED
     (PASSWORD_PROTECTED / NOT_CHECKED / identity "판단 불가")
  3. MISSING과 비-MISSING evidence 혼재             → PARTIAL
  4. 전부 MISSING                                  → MISSING
  5. VERSION_MISMATCH 존재                         → VERSION_MISMATCH
  6. SYSTEM_URL 존재(나머지 전부 MATCHED·정상)      → SYSTEM_URL
  7. 전부 MATCHED (identity 미기록은 잠정 MATCHED — ⑤ 후 재파생으로 확정)

identity 재판정 규칙: 사람이 게이트에서 정정하면 identity.result 자체를 갱신하고
decided_by를 확정 주체로, human_decision에 정정 내용을 기록한다 — 파생은 항상
result 값만 읽는다 (references/output_contract.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from config import (
    IDENTITY_MISMATCH,
    IDENTITY_UNDECIDABLE,
    INTEGRITY_DEFECT_CODES,
    INTEGRITY_UNVERIFIABLE_CODES,
    MATCH_FUZZY_AI,
    MODE_CHECKLIST,
    STATUS_EXCLUDED,
    STATUS_MATCHED,
    STATUS_MISSING,
    STATUS_PARTIAL,
    STATUS_SUSPECT,
    STATUS_SYSTEM_URL,
    STATUS_UNVERIFIED,
    STATUS_VERSION_MISMATCH,
    UNCLASSIFIED,
)

UNDECIDED: str = "미확정"


def _identity_result(entry: dict[str, Any]) -> str | None:
    identity = entry.get("identity")
    return identity.get("result") if isinstance(identity, dict) else None


def _is_defect(entry: dict[str, Any]) -> bool:
    """[결함 증거] — 파일이 evidence로서 결함이라는 증거가 있음 (설계서 §4.2 ③′)."""
    if entry.get("integrity") in INTEGRITY_DEFECT_CODES:
        return True
    return _identity_result(entry) == IDENTITY_MISMATCH


def _is_unverifiable(entry: dict[str, Any]) -> bool:
    """[확인 불가] — 정오를 확인할 수 없음. 결함으로 단정하지 않는다 (지침 4절)."""
    if entry.get("integrity") in INTEGRITY_UNVERIFIABLE_CODES:
        return True
    return _identity_result(entry) == IDENTITY_UNDECIDABLE


def derive_item_status(target: bool | None, evidence: list[dict[str, Any]]) -> str:
    """우선순위표(첫 일치 규칙)로 항목 상태를 파생한다 — 모드 A 전용."""
    if target is False:
        return STATUS_EXCLUDED
    if not evidence:
        return STATUS_MISSING
    if any(_is_defect(entry) for entry in evidence):
        return STATUS_SUSPECT
    if any(_is_unverifiable(entry) for entry in evidence):
        return STATUS_UNVERIFIED
    statuses = {entry.get("status") for entry in evidence}
    if STATUS_MISSING in statuses:
        return STATUS_PARTIAL if statuses != {STATUS_MISSING} else STATUS_MISSING
    if STATUS_VERSION_MISMATCH in statuses:
        return STATUS_VERSION_MISMATCH
    if STATUS_SYSTEM_URL in statuses:
        return STATUS_SYSTEM_URL
    return STATUS_MATCHED


def compute_unresolved(mapping: dict[str, Any]) -> dict[str, int]:
    """gate.unresolved 집계 (설계서 §4.2 ⑧) — 확정 시점의 미해결 잔존 근거."""
    fuzzy_unconfirmed = 0
    identity_open = 0
    for item in mapping.get("items", []):
        for entry in item.get("evidence", []):
            if entry.get("match_basis") == MATCH_FUZZY_AI \
                    and entry.get("decided_by", UNDECIDED) == UNDECIDED:
                fuzzy_unconfirmed += 1
            identity = entry.get("identity")
            if isinstance(identity, dict) \
                    and identity.get("result") in (IDENTITY_MISMATCH, IDENTITY_UNDECIDABLE) \
                    and identity.get("decided_by", UNDECIDED) == UNDECIDED:
                identity_open += 1
    # 모드 A: UNVERIFIED(확인 불가) / 모드 B: UNCLASSIFIED(추론 불가)를 같은 칸에 집계
    # (둘 다 "사람 확인 전까지 미해결"이라는 의미 — references/output_contract.md)
    unverified = sum(
        1 for item in mapping.get("items", [])
        if item.get("item_status") in (STATUS_UNVERIFIED, UNCLASSIFIED)
    )
    scope_gap_open = sum(
        1 for record in mapping.get("unclaimed_files") or []
        if record.get("scope_gap_candidate")
        and record.get("decided_by", UNDECIDED) == UNDECIDED
    )
    return {
        "fuzzy_unconfirmed": fuzzy_unconfirmed,
        "identity_open": identity_open,
        "unverified": unverified,
        "scope_gap_open": scope_gap_open,
    }


def recompute(mapping: dict[str, Any]) -> list[str]:
    """item_status·summary·gate.unresolved를 재계산해 mapping을 제자리 갱신한다.

    돌려주는 값은 변경 내역 설명 목록 (변경 없으면 빈 목록).
    """
    changes: list[str] = []
    if mapping["source"].get("mode") == MODE_CHECKLIST:
        for item in mapping["items"]:
            derived = derive_item_status(item.get("target"), item.get("evidence", []))
            if item.get("item_status") != derived:
                changes.append(f"{item['id']}: item_status {item.get('item_status')} → {derived}")
                item["item_status"] = derived
        target_items = [i for i in mapping["items"] if i.get("target")]
        by_status: dict[str, int] = {}
        for item in target_items:
            by_status[item["item_status"]] = by_status.get(item["item_status"], 0) + 1
        if mapping["summary"].get("by_status") != by_status:
            changes.append(f"summary.by_status → {by_status}")
            mapping["summary"]["by_status"] = by_status
    unresolved = compute_unresolved(mapping)
    if mapping["gate"].get("unresolved") != unresolved:
        changes.append(f"gate.unresolved → {unresolved}")
        mapping["gate"]["unresolved"] = unresolved
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="item_status·summary·unresolved 재파생 (⑤ 이후)")
    parser.add_argument("mapping")
    parser.add_argument("--check", action="store_true", help="차이만 출력, 파일 수정 안 함")
    args = parser.parse_args(argv)
    path = Path(args.mapping)
    mapping = json.loads(path.read_text(encoding="utf-8"))
    changes = recompute(mapping)
    if not changes:
        print("[OK] 재파생 결과 변경 없음")
        return 0
    for change in changes:
        print(f"  - {change}")
    if args.check:
        print(f"[CHECK] {len(changes)}건 차이 — 파일은 수정하지 않음")
        return 1
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {len(changes)}건 재파생 반영 → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
