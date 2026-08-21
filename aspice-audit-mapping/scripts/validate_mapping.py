"""mapping.json 통과 게이트 검증 (설계서 v0.4 §4.2 ⑥ / 모드별 규칙).

사용: python validate_mapping.py mapping.json [--inventory inventory.json]

v0.4: 커버리지 검사를 evidence 상태 기준으로 재기술 — PARTIAL 항목 안의 매칭
evidence도 integrity·identity 검사망에 포함된다. item_status는 파생 우선순위표
재계산과 대조해 정합을 확인한다 (derive_status.py 공용).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from config import (
    AI_ASSESSMENT_REQUIRED,
    IDENTITY_RESULTS,
    INTEGRITY_CODES,
    ITEM_STATUSES,
    INFERENCE_LEVELS,
    LINK_REASONS,
    MATCH_EXACT,
    MATCH_FUZZY_AI,
    MATCH_NORMALIZED,
    MODE_CHECKLIST,
    MODE_FOLDER,
    STATUS_MATCHED,
    STATUS_VERSION_MISMATCH,
)
from derive_status import compute_unresolved, derive_item_status

REQUIRED_TOP_KEYS = (
    "schema_version", "generated_at", "tool", "project", "source",
    "summary", "items", "unclaimed_files", "warnings", "gate",
)
UNCLAIMED_ID_RE = re.compile(r"^U-\d{3,}$")
UNRESOLVED_KEYS = ("fuzzy_unconfirmed", "identity_open", "unverified", "scope_gap_open")


def validate_mode_a(mapping: dict[str, Any], inventory_paths: set[str] | None) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for item in mapping["items"]:
        item_id = item.get("id", "(no id)")
        if item_id in seen_ids:
            errors.append(f"id 중복: {item_id}")
        seen_ids.add(item_id)
        if item.get("content_verified") is not False:
            errors.append(f"{item_id}: content_verified는 항상 false여야 함")
        status = item.get("item_status")
        if status not in ITEM_STATUSES:
            errors.append(f"{item_id}: 알 수 없는 item_status {status!r}")
        # v0.4: 파생 우선순위표 재계산과 대조 (결정론 정합)
        derived = derive_item_status(item.get("target"), item.get("evidence", []))
        if status != derived:
            errors.append(f"{item_id}: item_status {status!r}가 파생 규칙과 불일치 "
                          f"(재계산: {derived!r}) — derive_status.py 재실행 필요")
        for entry in item.get("evidence", []):
            basis = entry.get("match_basis")
            if basis not in (None, MATCH_EXACT, MATCH_NORMALIZED, MATCH_FUZZY_AI):
                errors.append(f"{item_id}: match_basis 값 오류 {basis!r}")
            if basis == MATCH_FUZZY_AI and not entry.get("decided_by"):
                errors.append(f"{item_id}: fuzzy_ai evidence에 decided_by 없음 (v0.4 evidence 레벨)")
            integrity = entry.get("integrity")
            if integrity is not None and integrity not in INTEGRITY_CODES:
                errors.append(f"{item_id}: integrity 값 오류 {integrity!r}")
            identity = entry.get("identity")
            if identity is not None and identity.get("result") not in IDENTITY_RESULTS:
                errors.append(f"{item_id}: identity.result 값 오류 {identity.get('result')!r}")
            # v0.4 ⑥: evidence 상태 기준 — 소속 item_status 무관 (PARTIAL 내부 매칭도 검사)
            if item.get("target") and entry.get("status") == STATUS_MATCHED:
                if integrity is None:
                    errors.append(f"{item_id}: MATCHED evidence에 integrity 없음")
                # identity는 열람 가능한 파일에만 요구 — integrity 비정상은 열람 생략(⑤b)
                if identity is None and integrity == "OK":
                    errors.append(f"{item_id}: MATCHED(integrity OK) evidence에 identity(정체성 확인) 없음")
            if item.get("target") and entry.get("status") == STATUS_VERSION_MISMATCH \
                    and entry.get("identity") is None and entry.get("candidates"):
                # 해소 후보가 있는 VERSION_MISMATCH도 identity 대상 (후보 파일 기준)
                errors.append(f"{item_id}: VERSION_MISMATCH(후보 있음)에 identity 없음")
            if inventory_paths is not None and entry.get("resolved_path") \
                    and entry["resolved_path"] not in inventory_paths:
                errors.append(f"{item_id}: resolved_path가 인벤토리에 없음 — {entry['resolved_path']}")
        if item.get("target") and status in AI_ASSESSMENT_REQUIRED:
            assessment = item.get("ai_assessment") or {}
            if not assessment.get("proposal") or not assessment.get("basis"):
                errors.append(f"{item_id}: {status} 항목에 ai_assessment(proposal/basis) 미작성")

    for record in mapping["unclaimed_files"]:
        record_id = record.get("id")
        if not record_id or not UNCLAIMED_ID_RE.match(str(record_id)):
            errors.append(f"unclaimed {record.get('path')}: id(U-nnn) 없음/형식 오류 (v0.4)")
        if record_id in seen_ids:
            errors.append(f"id 중복: {record_id}")
        seen_ids.add(record_id)
        if record.get("link_reason") not in LINK_REASONS:
            errors.append(f"unclaimed {record.get('path')}: link_reason 없음/오류")

    summary = mapping["summary"]
    target_items = [i for i in mapping["items"] if i.get("target")]
    actual: dict[str, int] = {}
    for item in target_items:
        actual[item["item_status"]] = actual.get(item["item_status"], 0) + 1
    if summary.get("by_status") != actual:
        errors.append(f"summary.by_status 불일치: {summary.get('by_status')} != {actual}")
    if summary.get("unclaimed_files") != len(mapping["unclaimed_files"]):
        errors.append("summary.unclaimed_files 불일치")
    actual_gaps = sum(1 for u in mapping["unclaimed_files"] if u.get("scope_gap_candidate"))
    if summary.get("scope_gap_candidates") != actual_gaps:
        errors.append("summary.scope_gap_candidates 불일치")
    return errors


def validate_mode_b(mapping: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for item in mapping["items"]:
        item_id = item.get("id", "(no id)")
        if item_id in seen_ids:
            errors.append(f"id 중복: {item_id}")
        seen_ids.add(item_id)
        if not item_id.startswith("F-"):
            errors.append(f"{item_id}: 모드 B id는 F-nnn 형식")
        inference = item.get("inference")
        if inference is None:
            errors.append(f"{item_id}: 모드 B 전 항목에 inference 필수")
            continue
        if inference.get("level") not in INFERENCE_LEVELS:
            errors.append(f"{item_id}: inference.level 값 오류 {inference.get('level')!r}")
        if item.get("item_status") != inference.get("level"):
            errors.append(f"{item_id}: item_status와 inference.level 불일치")
        if inference.get("level") != "UNCLASSIFIED" and not inference.get("basis"):
            errors.append(f"{item_id}: 추론 근거(basis) 없음 — 추측 분류 금지")
        if item.get("content_verified") is not False:
            errors.append(f"{item_id}: content_verified는 항상 false여야 함")
        if item.get("ai_assessment") is not None:
            errors.append(f"{item_id}: 모드 B에서 ai_assessment는 null")
    if mapping.get("unclaimed_files"):
        errors.append("모드 B에서 unclaimed_files는 빈 배열")
    if mapping.get("non_document_files") is None:
        errors.append("모드 B에서 non_document_files 필수")
    if mapping["summary"].get("by_inference") is None:
        errors.append("모드 B에서 summary.by_inference 필수")
    return errors


def validate(mapping: dict[str, Any], inventory_paths: set[str] | None) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in mapping:
            errors.append(f"최상위 필드 누락: {key}")
    if errors:
        return errors
    mode = mapping["source"].get("mode")
    if mode not in (MODE_CHECKLIST, MODE_FOLDER):
        return [f"source.mode 값 오류: {mode!r}"]
    errors.extend(validate_mode_a(mapping, inventory_paths) if mode == MODE_CHECKLIST
                  else validate_mode_b(mapping))
    gate = mapping["gate"]
    if gate.get("status") not in ("draft", "confirmed"):
        errors.append(f"gate.status 값 오류: {gate.get('status')!r}")
    if gate.get("status") == "confirmed" and not gate.get("confirmed_by"):
        errors.append("confirmed 상태인데 confirmed_by 없음 — 확정 주체(사람) 기록 필수")
    # v0.4: gate.unresolved 필수 + 재계산 정합 (확정 시점의 미해결 잔존 근거 — §4.2 ⑧)
    unresolved = gate.get("unresolved")
    if not isinstance(unresolved, dict) or any(k not in unresolved for k in UNRESOLVED_KEYS):
        errors.append(f"gate.unresolved 누락/형식 오류 — 필수 키: {UNRESOLVED_KEYS}")
    elif unresolved != compute_unresolved(mapping):
        errors.append(f"gate.unresolved 불일치: {unresolved} != 재계산 {compute_unresolved(mapping)}"
                      " — derive_status.py 재실행 필요")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mapping.json 검증 게이트")
    parser.add_argument("mapping")
    parser.add_argument("--inventory", default=None)
    args = parser.parse_args(argv)
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    inventory_paths: set[str] | None = None
    if args.inventory:
        inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
        inventory_paths = {str(r["relpath"]) for r in inventory["files"]}
    errors = validate(mapping, inventory_paths)
    if errors:
        print(f"[FAIL] {len(errors)}건:")
        for error in errors:
            print(f"  - {error}")
        return 1
    summary = mapping["summary"]
    mode = mapping["source"]["mode"]
    detail = summary.get("by_status") if mode == MODE_CHECKLIST else summary.get("by_inference")
    print(f"[PASS] mode={mode} — {detail}, 미참조 {summary.get('unclaimed_files')}건, "
          f"범위누락후보 {summary.get('scope_gap_candidates')}건, "
          f"gate={mapping['gate']['status']} (rev {mapping['gate']['revision']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
