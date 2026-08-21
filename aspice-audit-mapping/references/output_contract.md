# 출력 계약 — mapping.json (다음 단계 인터페이스 정본)

기계 검증 스키마는 `assets/mapping.schema.json`. 이 문서는 의미와 규칙을 정의한다.
2·3단계(프로세스 점검·산출물 내용 점검) 스킬은 **이 파일만 읽으면** 점검 대상과
증거 파일 위치를 알 수 있어야 한다.

## 계약 규칙 (파괴 금지)

1. **게이트 규칙**: 후속 스킬은 `gate.status != "confirmed"`이면 실행을 거부하고
   "1단계 매핑 확정 필요"를 안내한다. 판정 확정은 사람 — 파이프라인 구조로 강제.
2. **항목 참조는 `id`(T-nnn / F-nnn / U-nnn)로만.** 시트 행 번호·배열 순서에
   의존하지 않는다. id는 Target 시트의 No. 열에서 파생되며 재매핑 후에도 유지된다.
   유일성은 본 스킬이 보장한다 — No. 중복 시 `DUPLICATE_ITEM_NO`(FATAL)로 중단하고
   시트 정비를 요청한다 (자동 재부여 금지).
3. **`content_verified`는 1단계에서 항상 false.** 존재 확인 ≠ 내용 검증을
   계약 수준에서 분리한다. 이 필드를 true로 만드는 것은 3단계 스킬의 몫이다.
4. **`resolved_path`는 `source.deliverable_root` 기준 상대 경로.** 폴더를 옮겨도
   root만 갱신하면 계약이 유지된다. 산출물 루트는 **단일 전제** — 분산 폴더는
   상위 폴더로 모아 입력한다 (복수 루트는 향후 minor 확장 후보).
5. **스키마 확장은 필드 추가로만.** 기존 필드의 의미 변경·삭제 금지.
   하위 호환 추가는 minor, 파괴 변경은 major로 `schema_version` 갱신.
   상태 어휘(enum) 추가도 minor로 취급하되 후속 설계서 동기화를 거친다.
6. **다운스트림 수용 규칙 (v0.4)**: 후속 스킬은 `schema_version`의 **major==1이면
   수용**한다 (미지의 minor 추가 필드는 무시 가능). 특정 minor 버전 고정(pin)
   전제 검사는 금지.
7. **매핑 근거 불확실 취급 (v0.4)**: 후속 스킬은 `item_status`가 `SUSPECT` 또는
   `UNVERIFIED`, 또는 identity가 미해소(`identity.result != "일치"`이고
   decided_by가 "미확정")인 항목을 "매핑 근거 불확실"로 취급하고 해당 산출물
   점검 시 이를 표시한다. `gate.unresolved` 잔존 건수가 1차 근거다.

## 필드 의미 요약

| 경로 | 의미 |
|---|---|
| `source.scanned_at` | 폴더 스냅샷 시각 — 이 점검의 형상 기준 시점 |
| `source.listing_mode` | "filesystem" 또는 "listing" (device_list_dir 기반) |
| `summary.by_status` | item_status 집계 — validate가 items와 대조 |
| `items[].aspice.process` | PAM 4.0 프로세스 (그룹/산출물 규칙으로 결정론 부여) |
| `items[].aspice.oii_candidates` | OII 후보 — confidence "확인 필요" 동안 판정 근거로 사용 금지 |
| `items[].evidence[].status` | 엔트리 상태 (matching_rules.md 6종) |
| `items[].evidence[].candidates` | fuzzy 후보 — AI 확정 전 참고 정보 |
| `items[].item_status` | 항목 종합 상태 |
| `items[].ai_assessment` | AI 1차 제안 + 사용자 결정 기록 (ai_assessment.md 규칙) |
| `items[].remark` / `note` | 시트 비고·Note 원문 보존 — 후속 단계 점검 참고용 |
| `unclaimed_files[]` | 시트가 참조하지 않는 폴더 파일 + 성격 분류 |
| `warnings[]` | 파이프라인 경고 (예: RULER_DOCS_NOT_FOUND) |
| `gate` | 게이트 상태: status(draft/confirmed), confirmed_by/at, revision |

## 후속 단계가 기대할 수 있는 보장 (validate_mapping.py [PASS] 시)

- 점검 대상(target=true) 항목 전수에 item_status 존재 — **파생 우선순위표
  재계산과 일치** (derive_status.py 정합 검사)
- MISSING / VERSION_MISMATCH / SYSTEM_URL / PARTIAL / SUSPECT / UNVERIFIED
  항목 전수에 ai_assessment 존재
- status가 MATCHED인 evidence 전수(소속 item_status 무관)에 integrity·identity 존재
- summary 집계·gate.unresolved와 items 실측 일치
- MATCHED/PARTIAL 엔트리의 resolved_path가 인벤토리에 실존하는 경로
- id 유일성 (T-nnn / U-nnn 포함)

## 재매핑(revision)·승계 규칙 (v0.4 §4.4 — 정본)

`build_mapping.py --prev <이전 mapping.json>` 으로 실행하면 자동 적용된다.

1. **revision 보존**: 이전 revision은 출력 폴더의 `history/mapping_rev<N>.json`으로
   보존한다 (확정본 포함). 보존 실패 시 진행하지 않는다.
2. **human_decision 승계 (결정론)**: evidence의 3요소
   (`resolved_path`·`resolved_bytes`·`resolved_mtime`)가 이전 revision과 현 인벤토리에서
   **모두 동일**하면 그 evidence의 확정·identity 확인 결과를 승계하고
   `carried_over=true`를 기록한다. 하나라도 다르면 **무효화**하고
   diff.invalidated("재확인 필요" 목록)에 올린다. fuzzy 확정도 같은 조건으로 승계된다.
   항목 레벨 ai_assessment는 소속 evidence 전부 승계 + item_status 동일할 때만 승계.
   UNCLAIMED 분류는 path 동일 기준으로 승계.
3. **gate 리셋**: 재매핑 시 gate.status는 **무조건 draft로 리셋**, revision +1.
   재확정은 사용자 게이트를 다시 거친다.
4. **diff**: `mapping.diff`에 이전 대비 변경을 기록한다 — new_matches /
   resolved_missing / new_missing / status_changed / invalidated / items_added·removed.
   대시보드가 이를 렌더링한다.
5. **스냅샷 드리프트**: 한 실행 내에서도 ③′ 검사 시점의 파일 상태가 ② 인벤토리와
   다르면 `SNAPSHOT_DRIFT`(WARN) — 재스캔 권고 (ISO 33002 기준 시점 명확화).

## v0.3 추가 — 계약 1.2.0 변경분

- `source.mode`("checklist"|"folder_inferred"), `source.draft_origin`
- `evidence.match_basis`(exact|normalized|fuzzy_ai), `evidence.integrity`(6값),
  `evidence.identity`{result(일치|불일치|판단 불가), basis, decided_by, human_decision}
- `item_status`에 PARTIAL·SUSPECT 편입, `summary.by_status`에 SUSPECT,
  `summary.scope_gap_candidates`
- `unclaimed_files[]`: link_reason(NOT_LISTED|VERSION_SUPERSEDED|REJECTED_CANDIDATE),
  inferred{procedure_group, work_product, basis}, scope_gap_candidate, decided_by,
  human_decision
- 모드 B: id=F-nnn, inference{level, basis, content_checked, decided_by,
  human_decision, human_note} 전 항목 필수, summary.by_inference,
  non_document_files. 모드별 필수·금지는 스키마 oneOf 분기.
- 계약 규칙 추가: 2·3단계는 mode=="checklist"가 아니면 거부. SUSPECT 또는
  미해소 identity 불일치 항목은 "매핑 근거 불확실"로 표시.

## 입력 검증·파이프라인 코드 분류표 (정본 — v0.4 갱신)

| 코드 | 동작 | 시점 |
|---|---|---|
| CHECKLIST_UNREADABLE | FATAL | ⓪ |
| TARGET_SHEET_NOT_FOUND | PAUSE — 모드 B 제안 | ⓪ |
| MULTIPLE_TARGET_SHEETS | PAUSE — 시트 선택 | ⓪ |
| AI_DRAFT_CHECKLIST | PAUSE — 검수 확인 | ⓪ |
| DUPLICATE_ITEM_NO ★v0.4 | FATAL — No. 중복, 시트 정비 요청 (자동 재부여 금지) | ⓪~① |
| SHEET_STRUCTURE_MISMATCH | FATAL | ⓪~① |
| DELIVERABLE_ROOT_NOT_FOUND | FATAL | ⓪ |
| DELIVERABLE_ROOT_EMPTY | PAUSE — 경로 재확인 | ⓪ |
| CHECKLIST_FOUND_IN_FOLDER ★v0.4 | PAUSE — 모드 B 폴더에서 체크리스트 후보 발견, 모드 A 역제안 (자동 전환 금지) | B1 |
| UNPARSEABLE_ROWS | WARN | ① |
| UNKNOWN_PROCEDURE_GROUP | WARN | ④ |
| RULER_DOCS_NOT_FOUND | WARN — 산출물 폴더 기준 참고 경고. 잣대 확보의 정본 경로는 2단계의 별도 절차서 폴더 입력 | ④ |
| SNAPSHOT_DRIFT ★v0.4 | WARN — 스캔 후 파일 변경 검출, 재스캔 권고 | ③′ |
| CARRY_OVER_INVALIDATED ★v0.4 | WARN — 재매핑 승계 무효화 발생, 재확인 필요 목록 안내 | ④(--prev) |
| SCOPE_GAP_CANDIDATE | WARN | ⑤ |
| INTEGRITY_NOT_CHECKED | WARN — 구현 노트: listing 모드에서 파일 미접근, stage 후 재검사 필요 | ③′ |

## v0.4 추가 — 계약 1.3.0 변경분 (minor)

- `item_status`에 **UNVERIFIED**(확인 불가 — SUSPECT와 분리) 추가.
  `summary.by_status`에도 등장 가능.
- evidence 레벨 **`decided_by`**(스크립트/미확정/사람), **`human_decision`**
  (버전·경로 정정 등 기록처 — S3 시나리오), **`carried_over`**(재매핑 승계 표시).
- **`gate.unresolved`** {fuzzy_unconfirmed, identity_open, unverified, scope_gap_open}
  — 확정 시점의 미해결 잔존 건수. 미해결이 남아도 확정은 허용하되(확정 권한은 사람)
  숨기지 않고 기록한다. 모드 B의 unverified 칸은 UNCLASSIFIED 잔존 집계.
- `unclaimed_files[]`에 **`id`(U-nnn)** — 게이트 정정 참조용.
- `source.excluded_from_scan[]` — 인벤토리 제외 내역(INPUT_CHECKLIST·AI_DRAFT_MARKER).
- `non_document_files`는 **모드 공용** — 모드 A에서도 비문서 미참조의 집계처.
- `diff`(nullable) — 재매핑 시 이전 revision 대비 변경.
- identity 재판정 규칙: 사람이 게이트에서 정정하면 identity.result 자체를 갱신하고
  decided_by를 확정 주체로 바꾼다 — 파생·판독은 항상 result만 읽는다.
- ai_assessment 필수 대상에 **PARTIAL·UNVERIFIED** 포함
  (MISSING·VERSION_MISMATCH·SYSTEM_URL·PARTIAL·SUSPECT·UNVERIFIED).
- 커버리지 검사(⑥)는 **evidence 상태 기준**: status가 MATCHED(또는 후보 있는
  VERSION_MISMATCH)인 evidence 전수에 integrity·identity — 소속 item_status 무관.
  단 identity는 **integrity OK인 evidence에만** 요구한다 — 비정상 파일은
  열람 생략이 규칙이므로(⑤b) identity 부재가 정상이다.
