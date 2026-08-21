"""items + inventory → mapping.json 초안 생성 (설계서 v0.4, 계약 1.3.0 — 모드 공용).

모드 A: python build_mapping.py items.json inventory.json --project .. --phase .. -o mapping.json
모드 B: python build_mapping.py --mode folder_inferred inventory.json --project .. --phase .. -o mapping.json
       (모드 B는 items 인자 생략 — 문서 파일 1개 = 항목 1개)
재매핑: --prev <이전 mapping.json> 추가 → §4.4 규칙 적용
       (이전 revision을 history/에 보존, 3요소 불변 evidence의 확정 승계,
        변경분 무효화, diff 산출, gate=draft 리셋·revision+1)

무결성 검사(③′)는 --file-root 가 주어지면 실파일로 수행하고, 없으면(listing 모드)
NOT_CHECKED + 경고를 남긴다 (stage 후 재검사 필요 — 구현 노트).
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import unicodedata
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import (
    AI_ASSESSMENT_REQUIRED,
    INTEGRITY_NOT_CHECKED,
    LINK_NOT_LISTED,
    LINK_REJECTED_CANDIDATE,
    LINK_VERSION_SUPERSEDED,
    MODE_CHECKLIST,
    MODE_FOLDER,
    SCHEMA_VERSION,
    SKILL_NAME,
    SKILL_VERSION,
    STATUS_MATCHED,
    STATUS_MISSING,
    UNCLASSIFIED,
)
from derive_status import compute_unresolved, derive_item_status
from infer_mapping import infer_from_path
from match_evidence import EvidenceResult, InventoryIndex, normalize
from verify_matched_files import check_integrity

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DRIFT_TOLERANCE_SECONDS = 2.0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_group_name(name: str) -> str:
    text = unicodedata.normalize("NFC", name)
    return " ".join(text.replace("\n", " ").split())


def resolve_group(raw_group: str, oii_map: dict[str, Any]) -> tuple[str, bool]:
    """(표준 그룹명 또는 원문, 매칭 성공 여부) — §5.1 정규화→정확→별칭→fallback."""
    name = normalize_group_name(raw_group)
    if name in oii_map["group_to_process"]:
        return name, True
    alias = oii_map.get("group_aliases", {}).get(name)
    if alias:
        return alias, True
    return name, False


def resolve_aspice(group: str, group_known: bool, work_product: str,
                   oii_map: dict[str, Any]) -> dict[str, Any]:
    if not group_known:
        return {"process": None, "oii_candidates": [],
                "confidence": "매핑 불가 — 확인 필요",
                "basis": "UNKNOWN_PROCEDURE_GROUP — 표준 12종·별칭 표 미일치"}
    group_processes: list[str] = oii_map["group_to_process"].get(group, [])
    process: str | None = group_processes[0] if len(group_processes) == 1 else None
    oii_candidates: list[str] = []
    basis = "assets/oii_map.json group_to_process"
    for rule in oii_map["work_product_rules"]:
        if rule["contains"] in work_product and (not group_processes or rule["process"] in group_processes):
            process = rule["process"]
            oii_candidates = list(rule.get("oii_candidates", []))
            basis = f"assets/oii_map.json work_product_rules('{rule['contains']}')"
            break
    if process is None and group_processes:
        process = "/".join(group_processes)
    return {"process": process, "oii_candidates": oii_candidates,
            "confidence": "확인 필요", "basis": basis}


def empty_ai_assessment() -> dict[str, Any]:
    return {"proposal": None, "basis": None, "where_to_look": None,
            "decided_by": "미확정", "human_decision": None, "human_note": None}


def integrity_for(resolved_path: str | None, file_root: Path | None) -> str:
    if resolved_path is None or file_root is None:
        return INTEGRITY_NOT_CHECKED
    return check_integrity(file_root / resolved_path)


def check_snapshot_drift(record_map: dict[str, dict[str, Any]], resolved_path: str,
                         file_root: Path, drifted: list[str]) -> None:
    """②의 인벤토리와 검사 시점 파일 상태를 대조한다 (설계서 §4.4-6 — filesystem 전용)."""
    record = record_map.get(resolved_path)
    actual = file_root / resolved_path
    if record is None or not actual.is_file():
        return
    stat = actual.stat()
    recorded_size = record.get("size")
    if recorded_size is not None and stat.st_size != recorded_size:
        drifted.append(resolved_path)
        return
    recorded_mtime = record.get("mtime")
    if recorded_mtime:
        try:
            recorded = datetime.fromisoformat(str(recorded_mtime)).timestamp()
            if abs(stat.st_mtime - recorded) > DRIFT_TOLERANCE_SECONDS:
                drifted.append(resolved_path)
        except ValueError:
            pass


def link_reason_for(record: dict[str, Any], index: InventoryIndex) -> str:
    base = normalize(str(record["name"])).base
    if base and base in index.matched_bases:
        return LINK_VERSION_SUPERSEDED
    if str(record["relpath"]) in index.fuzzy_candidate_paths:
        return LINK_REJECTED_CANDIDATE
    return LINK_NOT_LISTED


def build_mode_a(items_doc: dict[str, Any], inventory: dict[str, Any],
                 oii_map: dict[str, Any], file_root: Path | None,
                 warnings: list[dict[str, str]]
                 ) -> tuple[list[dict], list[dict], list[dict]]:
    """모드 A: (items, unclaimed_files[문서류], non_document_files)를 만든다."""
    index = InventoryIndex(inventory["files"])
    record_map = {str(r["relpath"]): r for r in inventory["files"] if r["kind"] == "file"}
    filesystem_mode = inventory.get("mode") == "filesystem"
    mapped_items: list[dict[str, Any]] = []
    claimed_paths: set[str] = set()
    unknown_groups: set[str] = set()
    drifted: list[str] = []

    for item in items_doc["items"]:
        group, group_known = resolve_group(item["procedure_group"], oii_map)
        if not group_known and group not in unknown_groups:
            unknown_groups.add(group)
            warnings.append({"code": "UNKNOWN_PROCEDURE_GROUP",
                             "message": f"표준 12종·별칭 표에 없는 절차그룹: '{group}' (No.{item['no']}) — process=null 진행"})
        evidence: list[EvidenceResult] = []
        if item["target"]:
            for entry_text in item["listed_entries"]:
                entry = index.match(entry_text)
                if entry.resolved_path:
                    # 중복 claim 허용(1파일 N행 — matching_rules.md): claimed 집합에만 추가
                    claimed_paths.add(entry.resolved_path)
                    entry.integrity = integrity_for(entry.resolved_path, file_root)
                    if filesystem_mode and file_root is not None:
                        check_snapshot_drift(record_map, entry.resolved_path, file_root, drifted)
                evidence.append(entry)
        evidence_dicts = [asdict(entry) for entry in evidence]
        item_status = derive_item_status(item["target"], evidence_dicts)
        mapped_items.append({
            "id": f"T-{item['no']:03d}",
            "no": item["no"],
            "procedure_group": group,
            "work_product": item["work_product"],
            "target": item["target"],
            "excluded_reason": item["remark"] if not item["target"] else None,
            "aspice": resolve_aspice(group, group_known, item["work_product"], oii_map),
            "evidence": evidence_dicts,
            "item_status": item_status,
            "content_verified": False,
            "inference": None,
            "remark": item["remark"],
            "note": item["note"],
            "ai_assessment": empty_ai_assessment() if item_status in AI_ASSESSMENT_REQUIRED else None,
        })

    if drifted:
        unique_drifted = sorted(set(drifted))  # 중복 claim(1파일 N행) 중복 제거
        warnings.append({"code": "SNAPSHOT_DRIFT",
                         "message": f"스캔 이후 변경된 파일 {len(unique_drifted)}건 — 재스캔(재매핑) 권고: "
                                    + ", ".join(unique_drifted[:5])})

    # UNCLAIMED 리포팅 — v0.4: 문서류만 개별 항목화(U-id), 비문서는 집계 전용
    listed_products = {normalize_group_name(i["work_product"]).lower() for i in items_doc["items"]}
    unclaimed: list[dict[str, Any]] = []
    non_documents: list[dict[str, Any]] = []
    scope_gap_count = 0
    for record in sorted(inventory["files"], key=lambda r: str(r["relpath"])):
        if record["kind"] != "file" or record["relpath"] in claimed_paths:
            continue
        if not record.get("document"):
            non_documents.append({"path": record["relpath"],
                                  "ext": Path(str(record["name"])).suffix.lower()})
            continue
        inference = infer_from_path(str(record["relpath"]), oii_map.get("keyword_dict", []))
        inferred = None
        scope_gap = False
        if inference.level != UNCLASSIFIED:
            inferred = {"procedure_group": inference.procedure_group,
                        "work_product": inference.work_product, "basis": inference.basis}
            reason = link_reason_for(record, index)
            if (reason == LINK_NOT_LISTED
                    and inference.work_product
                    and normalize_group_name(inference.work_product).lower() not in listed_products):
                scope_gap = True
                scope_gap_count += 1
        unclaimed.append({
            "id": f"U-{len(unclaimed) + 1:03d}",
            "path": record["relpath"],
            "link_reason": link_reason_for(record, index),
            "classification": None,
            "inferred": inferred,
            "scope_gap_candidate": scope_gap,
            "decided_by": "미확정",
            "human_decision": None,
            "ai_note": None,
            "basis": None,
        })
    if scope_gap_count:
        warnings.append({"code": "SCOPE_GAP_CANDIDATE",
                         "message": f"미참조 파일 {scope_gap_count}건이 표준 산출물로 추정되나 Target 시트에 대응 행 없음 — 점검 범위 보완 검토 필요(목록: 미참조 리포트)"})
    return mapped_items, unclaimed, non_documents


def build_mode_b(inventory: dict[str, Any], oii_map: dict[str, Any],
                 file_root: Path | None) -> tuple[list[dict], list[dict]]:
    """모드 B: 문서 파일 1개 = 항목 1개. (items, non_document_files)."""
    items: list[dict[str, Any]] = []
    non_documents: list[dict[str, Any]] = []
    sequence = 0
    for record in inventory["files"]:
        if record["kind"] != "file":
            continue
        if not record.get("document"):
            non_documents.append({"path": record["relpath"],
                                  "ext": Path(str(record["name"])).suffix.lower()})
            continue
        sequence += 1
        integrity = integrity_for(str(record["relpath"]), file_root)
        inference = infer_from_path(str(record["relpath"]), oii_map.get("keyword_dict", []))
        items.append({
            "id": f"F-{sequence:03d}",
            "no": None,
            "procedure_group": inference.procedure_group,
            "work_product": inference.work_product,
            "target": None,
            "excluded_reason": None,
            "aspice": {"process": inference.pam, "oii_candidates": [],
                       "confidence": "확인 필요" if inference.pam else "매핑 불가 — 확인 필요",
                       "basis": inference.basis or "키워드 사전 미매칭"},
            "evidence": [{
                "listed": None, "status": None, "match_basis": None,
                "decided_by": None, "human_decision": None, "carried_over": False,
                "integrity": integrity, "identity": None,
                "resolved_path": record["relpath"],
                "resolved_mtime": record.get("mtime"),
                "resolved_bytes": record.get("size"),
                "version_note": None, "candidates": [],
            }],
            "item_status": inference.level,
            "content_verified": False,
            "inference": {"level": inference.level, "basis": inference.basis,
                          "content_checked": False, "decided_by": "미확정",
                          "human_decision": None, "human_note": None},
            "remark": "", "note": "",
            "ai_assessment": None,
        })
    return items, non_documents


# ── §4.4 재매핑: 승계·무효화·diff ────────────────────────────────

def _evidence_key(entry: dict[str, Any]) -> str:
    return str(entry.get("listed"))


def _file_unchanged(record_map: dict[str, dict[str, Any]], entry: dict[str, Any]) -> bool:
    """이전 evidence의 3요소(resolved_path·bytes·mtime)가 현 인벤토리와 동일한가."""
    path = entry.get("resolved_path")
    if not path:
        return False
    record = record_map.get(str(path))
    if record is None:
        return False
    return (record.get("size") == entry.get("resolved_bytes")
            and record.get("mtime") == entry.get("resolved_mtime"))


def _had_human_input(entry: dict[str, Any]) -> bool:
    if entry.get("human_decision"):
        return True
    identity = entry.get("identity")
    if isinstance(identity, dict) and (identity.get("human_decision")
                                       or identity.get("decided_by") not in (None, "미확정")):
        return True
    return entry.get("decided_by") not in (None, "미확정", "스크립트")


def apply_carry_over(mapping: dict[str, Any], prev: dict[str, Any],
                     inventory: dict[str, Any]) -> dict[str, Any]:
    """이전 revision의 확정·확인 결과를 3요소 불변 조건으로 승계한다 (§4.4-2).

    돌려주는 값은 diff 요약 (mapping["diff"]에 기록).
    """
    record_map = {str(r["relpath"]): r for r in inventory["files"] if r["kind"] == "file"}
    prev_items = {item["id"]: item for item in prev.get("items", [])}
    invalidated: list[dict[str, str]] = []

    for item in mapping["items"]:
        prev_item = prev_items.get(item["id"])
        if prev_item is None:
            continue
        prev_by_key = {_evidence_key(e): e for e in prev_item.get("evidence", [])}
        all_carried = bool(item.get("evidence"))
        for position, entry in enumerate(item.get("evidence", [])):
            prev_entry = prev_by_key.get(_evidence_key(entry))
            if prev_entry is None:
                all_carried = False
                continue
            if _file_unchanged(record_map, prev_entry):
                carried = dict(prev_entry)
                carried["carried_over"] = True
                # 이번 실행에서 새로 계산된 무결성이 있으면 그것을 우선한다
                if entry.get("integrity") not in (None, INTEGRITY_NOT_CHECKED):
                    carried["integrity"] = entry["integrity"]
                item["evidence"][position] = carried
            else:
                all_carried = False
                if _had_human_input(prev_entry):
                    invalidated.append({
                        "id": item["id"], "listed": str(prev_entry.get("listed")),
                        "reason": "근거 파일 변경·소실 — 이전 확정 무효화, 재확인 필요",
                    })
        # 항목 레벨 ai_assessment 승계: evidence 전부 승계 + 상태 동일할 때만
        item_status = derive_item_status(item.get("target"), item.get("evidence", []))
        item["item_status"] = item_status
        if (all_carried and prev_item.get("item_status") == item_status
                and prev_item.get("ai_assessment") and item.get("ai_assessment") is not None):
            item["ai_assessment"] = dict(prev_item["ai_assessment"])

    # UNCLAIMED 분류 승계 (path 동일 기준)
    prev_unclaimed = {str(u.get("path")): u for u in prev.get("unclaimed_files") or []}
    for record in mapping.get("unclaimed_files", []):
        prev_record = prev_unclaimed.get(str(record["path"]))
        if prev_record is None:
            continue
        for key in ("classification", "decided_by", "human_decision", "ai_note", "basis"):
            if prev_record.get(key) is not None:
                record[key] = prev_record[key]

    # diff 산출 (id 기준)
    new_status = {item["id"]: item["item_status"] for item in mapping["items"]}
    old_status = {item["id"]: item.get("item_status") for item in prev.get("items", [])}
    status_changed = [
        {"id": item_id, "from": old_status[item_id], "to": status}
        for item_id, status in new_status.items()
        if item_id in old_status and old_status[item_id] != status
    ]
    return {
        "previous_revision": prev.get("gate", {}).get("revision"),
        "new_matches": [c["id"] for c in status_changed
                        if c["to"] == STATUS_MATCHED],
        "resolved_missing": [c["id"] for c in status_changed
                             if c["from"] == STATUS_MISSING and c["to"] != STATUS_MISSING],
        "new_missing": [c["id"] for c in status_changed
                        if c["to"] == STATUS_MISSING],
        "status_changed": status_changed,
        "invalidated": invalidated,
        "items_added": sorted(set(new_status) - set(old_status)),
        "items_removed": sorted(set(old_status) - set(new_status)),
    }


def preserve_history(prev_path: Path, prev: dict[str, Any], output_path: Path) -> None:
    """이전 revision을 history/에 보존한다 — 실패 시 진행 중단 (§4.4-1)."""
    history_dir = output_path.parent / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    revision = prev.get("gate", {}).get("revision", 0)
    destination = history_dir / f"mapping_rev{revision}.json"
    shutil.copy2(prev_path, destination)
    if not destination.is_file():
        raise SystemExit(f"[중단] 이전 revision 보존 실패: {destination}")
    logger.info("이전 revision 보존 → %s", destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mapping.json 초안 생성 (모드 공용)")
    parser.add_argument("items", nargs="?", default=None, help="items.json (모드 A)")
    parser.add_argument("inventory", help="inventory.json")
    parser.add_argument("--mode", default=MODE_CHECKLIST, choices=[MODE_CHECKLIST, MODE_FOLDER])
    parser.add_argument("--project", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--revision", type=int, default=None,
                        help="명시 지정 시 그 값 사용 (기본: 1 또는 prev+1)")
    parser.add_argument("--prev", default=None,
                        help="재매핑 시 이전 mapping.json — §4.4 승계·diff·history 보존")
    parser.add_argument("--file-root", default=None,
                        help="무결성 검사용 실파일 루트 (없으면 NOT_CHECKED + 경고)")
    parser.add_argument("--draft-origin", default=None,
                        help="AI 초안 출신 체크리스트 사용 시 이력 문자열")
    parser.add_argument("--oii-map", default=str(ASSETS_DIR / "oii_map.json"))
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.mode == MODE_CHECKLIST and args.items is None:
        parser.error("모드 A에는 items.json이 필요합니다")
    inventory = load_json(Path(args.inventory))
    oii_map = load_json(Path(args.oii_map))
    file_root = Path(args.file_root) if args.file_root else None
    warnings: list[dict[str, str]] = []

    prev: dict[str, Any] | None = None
    if args.prev:
        prev = load_json(Path(args.prev))
        if prev["source"].get("mode") != args.mode:
            raise SystemExit(f"[중단] 이전 mapping 모드({prev['source'].get('mode')})와 현재 모드({args.mode}) 불일치")

    if file_root is None:
        warnings.append({"code": "INTEGRITY_NOT_CHECKED",
                         "message": "실파일 미접근(listing 모드) — 무결성·정체성 검사를 위해 매칭 파일 stage 후 재실행 필요"})

    items_doc: dict[str, Any] | None = None
    if args.mode == MODE_CHECKLIST:
        items_doc = load_json(Path(args.items))
        for row in items_doc.get("unparseable_rows", []):
            warnings.append({"code": "UNPARSEABLE_ROWS",
                             "message": f"행 {row['row']} 해석 불가({row['reason']}) — 수기 확인 필요: {row.get('work_product')}"})
        items, unclaimed, non_documents = build_mode_a(items_doc, inventory, oii_map, file_root, warnings)
    else:
        items, non_documents = build_mode_b(inventory, oii_map, file_root)
        unclaimed = []

    # 잣대 문서 경고 (ruler_patterns) — v0.4 문구: 2단계 별도 절차서 폴더 입력과 정합
    inventory_names = " ".join(str(r["name"]) for r in inventory["files"])
    if not any(pattern in inventory_names for pattern in oii_map.get("ruler_patterns", [])):
        warnings.append({"code": "RULER_DOCS_NOT_FOUND",
                         "message": "산출물 폴더에 잣대 문서(사내 절차서·표준 템플릿) 없음 — "
                                    "2단계는 별도 절차서 폴더 입력이 기본 경로이므로 그쪽으로 확보 예정이면 무시 가능"})

    if args.mode == MODE_CHECKLIST:
        target_items = [i for i in items if i["target"]]
        by_status: dict[str, int] = {}
        for item in target_items:
            by_status[item["item_status"]] = by_status.get(item["item_status"], 0) + 1
        summary = {
            "total_items": len(items), "target_items": len(target_items),
            "excluded_items": len(items) - len(target_items),
            "by_status": by_status, "by_inference": None,
            "unclaimed_files": len(unclaimed),
            "scope_gap_candidates": sum(1 for u in unclaimed if u["scope_gap_candidate"]),
        }
    else:
        by_inference: dict[str, int] = {}
        for item in items:
            by_inference[item["item_status"]] = by_inference.get(item["item_status"], 0) + 1
        by_inference["NON_DOCUMENT"] = len(non_documents)
        summary = {
            "total_items": len(items), "target_items": None, "excluded_items": None,
            "by_status": None, "by_inference": by_inference,
            "unclaimed_files": 0, "scope_gap_candidates": 0,
        }

    revision = args.revision if args.revision is not None else (
        (prev.get("gate", {}).get("revision", 0) + 1) if prev else 1
    )
    mapping = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(tz=timezone.utc).astimezone().isoformat(),
        "tool": {"skill": SKILL_NAME, "skill_version": SKILL_VERSION},
        "project": {"name": args.project, "phase": args.phase},
        "source": {
            "mode": args.mode,
            "checklist_file": items_doc["source_file"] if items_doc else None,
            "checklist_sheet": items_doc["sheet"] if items_doc else None,
            "template_version": None,
            "draft_origin": args.draft_origin,
            "deliverable_root": inventory["root"],
            "listing_mode": inventory["mode"],
            "scanned_at": inventory["scanned_at"],
            "file_count": sum(1 for r in inventory["files"] if r["kind"] == "file"),
            "excluded_from_scan": inventory.get("excluded_from_scan", []),
        },
        "summary": summary,
        "items": items,
        "unclaimed_files": unclaimed,
        "non_document_files": non_documents,
        "warnings": warnings,
        "diff": None,
        "gate": {"status": "draft", "confirmed_by": None, "confirmed_at": None,
                 "revision": revision,
                 "unresolved": {"fuzzy_unconfirmed": 0, "identity_open": 0,
                                "unverified": 0, "scope_gap_open": 0}},
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if prev is not None:
        preserve_history(Path(args.prev), prev, output_path)
        mapping["diff"] = apply_carry_over(mapping, prev, inventory)
        # 승계 후 summary 재집계 (상태가 승계로 바뀔 수 있음)
        if args.mode == MODE_CHECKLIST:
            target_items = [i for i in mapping["items"] if i["target"]]
            by_status = {}
            for item in target_items:
                by_status[item["item_status"]] = by_status.get(item["item_status"], 0) + 1
            mapping["summary"]["by_status"] = by_status
        if mapping["diff"]["invalidated"]:
            warnings.append({"code": "CARRY_OVER_INVALIDATED",
                             "message": f"근거 파일 변경으로 이전 확정 {len(mapping['diff']['invalidated'])}건 무효화 — 재확인 필요 목록 확인"})
    mapping["gate"]["unresolved"] = compute_unresolved(mapping)

    output_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("초안 생성 [%s rev%d]: 항목 %d, 미참조 %d(문서류), 비문서 %d, 경고 %d → %s",
                args.mode, revision, len(items), len(unclaimed),
                len(non_documents), len(warnings), output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
