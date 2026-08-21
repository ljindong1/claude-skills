---
name: aspice-audit-mapping
description: ASPICE 품질점검(오디트) 1단계 — 체크리스트의 Target 시트(점검 대상 산출물 목록)와 산출물 폴더를 대조해 매핑·검증(무결성·정체성)하고 HTML 대시보드로 시각화하는 스킬. Target 시트가 없으면 폴더만으로 절차그룹을 추론해 현황을 보여주고 Target 시트 초안을 역생성하는 모드 B도 지원한다. 사용자가 "산출물 매핑", "매핑 돌려줘", "점검 대상 매핑", "Target 시트 매핑", "산출물 현황 시각화", "체크리스트랑 폴더 대조", "누락 산출물 확인", "evidence 매핑", "매핑 대시보드", "오디트 1단계", "재매핑", "매핑 확정", "체크리스트 없이 폴더만으로 현황 파악", "폴더 보고 산출물 분류", "Target 시트 초안 만들어" 등을 언급하거나, ASPICE 품질점검 체크리스트(.xlsx)와 산출물 폴더(또는 폴더만)를 주며 산출물 현황 확인·시각화를 원하면 반드시 이 스킬을 사용하라. 결과는 mapping.json(2단계 입력 계약 — 모드 A 확정본만 유효)과 self-contained HTML 대시보드이며, 매핑 확정(gate confirmed)은 반드시 사용자가 한다. 체크리스트 항목의 내용 점검(Pass/Fail 판정, 코멘트 작성)이나 종합 리포트 작성은 이 스킬의 범위가 아니다 — 이 스킬은 존재·정체 확인과 매핑까지만 한다.
---

# aspice-audit-mapping — 오디트 1단계: 산출물 매핑·검증·시각화

체크리스트 Target 시트 기준 매핑(**모드 A**, 정식 경로)과 폴더 추론 매핑
(**모드 B**, 보조 경로 — Target 시트 초안 역생성)을 수행한다.
MATCHED는 "존재 + 무결성 + 정체성(이 파일이 그 산출물이 맞음)"까지 확인된
상태다. v0.4(계약 1.3.0)부터 **"불일치 증거 있음"(SUSPECT)과 "확인 불가"
(UNVERIFIED)를 분리**한다 — 확인하지 못한 것을 틀렸다고 단정하지 않는다.
단 내용 **적정성**은 판정하지 않는다 — 2·3단계의 몫.

## 불변 원칙 (우회 설계 금지)

1. **매핑 확정은 사람.** AI 관여 지점(fuzzy_ai 매칭, identity, UNCLAIMED 분류,
   모드 B 추론)은 전부 decided_by/match_basis로 표시되고, gate confirmed는
   사용자 확정 후에만 기록한다.
2. **존재·정체 ≠ 수행·적정.** content_verified는 항상 false. AI 파일 열람은
   무결성·정체성·분류 목적으로 표지·제목·목차·서두 수준까지만 — 내용 적정성
   판단·코멘트 생성 금지. **열람 전에는 모드 불문 건수를 보고하고 승인받는다.**
3. **추측 금지.** 근거 없는 매칭·분류·판정을 만들지 않는다. 모드 자동 전환 금지,
   identity "판단 불가"·암호 보호를 불일치로 단정 금지(→ UNVERIFIED),
   UNCLASSIFIED 추측 분류 금지.
4. **결정론 작업은 스크립트로**: 검증·파싱·스캔·매칭·무결성·link_reason·추론 1차·
   **item_status 파생(derive_status.py — AI가 손으로 고치지 않는다)**·
   재매핑 승계·커버리지·대시보드·초안 생성.
5. **모드 B는 본선 비합류**: 그 mapping.json은 confirmed여도 2단계 입력 불가.
   초안 .xlsx의 `_ai_draft_meta` 마커로 미검수 재입력을 차단한다.

## 워크플로 — 모드 판별과 ⓪ 입력 검증

```bash
python scripts/validate_inputs.py --checklist <xlsx> --root <폴더>   # 모드 A
python scripts/validate_inputs.py --root <폴더>                      # 모드 B 사전 검증
```

결과 코드에 따라 행동한다 (분류표 정본: `references/output_contract.md`):
**FATAL**(중단·원인 안내) / **PAUSE**(사용자에게 물어 분기 — Target 시트 없음 →
모드 B 제안, 다중 Target 시트 → 선택 요청, AI 초안 마커 → 검수 확인, 빈 폴더 →
경로 재확인) / **WARN**(기록 후 진행). Target 시트가 없다고 조용히 모드 B로
넘어가지 않는다 — 항상 사용자 확인.

## 모드 A (체크리스트 매핑 — 정식 경로)

```bash
python scripts/parse_target_sheet.py <체크리스트.xlsx> -o work/items.json       # ①
python scripts/scan_deliverables.py --root <폴더> \
    --exclude-checklist "<체크리스트 파일명>" -o work/inventory.json            # ②
python scripts/build_mapping.py work/items.json work/inventory.json \
    --project "<프로젝트>" --phase "<단계>" --file-root <폴더> -o work/mapping.json  # ③③′④
```

- ② `--exclude-checklist`로 입력 체크리스트 자신을 인벤토리에서 제외한다
  (UNCLAIMED 노이즈 방지 — `_ai_draft_meta` 마커 파일·임시파일도 자동 제외).
- ① No. 중복이 있으면 `DUPLICATE_ITEM_NO`(FATAL) — 시트 정비를 요청하고 중단.
- ③′ 무결성 검사는 `--file-root`(실파일 접근)가 있어야 수행된다.
  **Cowork 클라우드에서 listing 모드로 스캔한 경우, 매칭된 파일을
  device_stage_files로 stage한 뒤 그 경로를 --file-root로 다시 실행**해야
  integrity가 채워진다. 미접근 시 NOT_CHECKED(→UNVERIFIED) + 경고가 남는다.
- 매칭 규칙·상태·파생 우선순위표·link_reason은 `references/matching_rules.md`.

### ⑤ AI 단계 (references/ai_assessment.md 필수 선독)

0. **⑤-b0 열람 게이트**: 정체성 확인 대상(MATCHED·VERSION_MISMATCH evidence)
   건수를 사용자에게 보고하고 진행 확인 — 과다하면 절차그룹 단위 분할 제안.
1. **fuzzy 후보 확정 제안** — match_basis="fuzzy_ai", evidence.decided_by="미확정".
2. **정체성 확인**: 승인 후, 대상 evidence 전수의 파일을 열어 표지·제목·머리말·
   개정이력 수준(형식별 앵커는 ai_assessment.md)에서 "일치/불일치/판단 불가"
   3값 + 근거를 evidence.identity에 기록. 적정성 언급 금지.
3. **UNCLAIMED 리포팅**(문서류만 — 비문서는 집계 전용): link_reason은 스크립트
   산출값 유지, 성격 분류 제안 + 키워드 사전 추정 검토. 표준 산출물로 추정되는데
   시트에 대응 행이 없으면 scope_gap_candidate 확인 (보완 여부는 사람).
4. **재파생**: `python scripts/derive_status.py work/mapping.json` —
   identity 반영 후 item_status·summary·gate.unresolved를 스크립트로 재계산.
   AI가 item_status를 직접 고치지 않는다.
5. **ai_assessment 작성**: MISSING·VERSION_MISMATCH·SYSTEM_URL·PARTIAL·SUSPECT·
   UNVERIFIED 전수. UNVERIFIED는 "확인 불가 사유 + 사람이 확인할 사항"으로 쓴다.

### ⑥⑦⑧ 검증 → 대시보드 → 사용자 게이트

```bash
python scripts/validate_mapping.py work/mapping.json --inventory work/inventory.json
python scripts/build_dashboard.py work/mapping.json -o work/dashboard.html
```

[PASS] 필수. 게이트에서 fuzzy_ai 매칭·identity 불일치/판단 불가·UNVERIFIED·
UNCLAIMED 분류(U-id로 참조)·SCOPE_GAP_CANDIDATE를 별도 검토 목록으로 제시하고,
정정 반영(사람 정정은 evidence.human_decision / identity.result 갱신) →
derive_status.py 재실행 → 재검증.

**확정 조건 (§4.2 ⑧)**: "매핑 확정" 요청 시 미해결 잔존(gate.unresolved —
fuzzy 미확정·identity 미해소·UNVERIFIED·scope_gap 미결) 건수를 요약 고지한다.
미해결이 남아도 사용자가 인지하고 확정하면 허용하되(확정 권한은 사람) 차단하지
않고 gate.unresolved에 기록을 남긴다 — 2·3단계가 "매핑 근거 불확실" 취급의
근거로 삼는다. 확정 시 gate.status="confirmed" + confirmed_by/at 기록.

## 모드 B (폴더 추론 매핑 — 보조 경로)

상세 절차·원칙은 `references/folder_inference.md` (필수 선독). 요지:

```bash
python scripts/scan_deliverables.py --root <폴더> -o work/inventory.json        # B1
python scripts/build_mapping.py --mode folder_inferred work/inventory.json \
    --project "<프로젝트>" --phase "<단계>" --file-root <폴더> -o work/mapping.json  # B2~B3
# B4: INFERRED_LOW·UNCLASSIFIED 건수를 사용자에게 보고 → 열람 승인 후
# B5: AI가 승인분만 내용 확인(제목·목차·서두) → inference 갱신 (분류 목적 한정)
python scripts/validate_mapping.py work/mapping.json                             # B6
python scripts/build_dashboard.py work/mapping.json -o work/dashboard.html       # B7 (추론 배너)
# B8: 사용자 게이트 → 확정
python scripts/generate_target_draft.py work/mapping.json -o work/Target시트초안.xlsx  # B9 (+마커)
```

## 재매핑 (모드 공용 — §4.4, references/output_contract.md 정본)

```bash
python scripts/build_mapping.py work/items.json work/inventory.json \
    --prev work/mapping.json --project .. --phase .. --file-root .. -o work/mapping.json
```

`--prev`가 §4.4 규칙을 자동 적용한다: 이전 revision을 `history/`에 보존(실패 시
중단) → 3요소(resolved_path·bytes·mtime) 불변 evidence의 확정·identity를 승계
(carried_over=true) → 변경분은 무효화하고 "재확인 필요" 목록(diff.invalidated)에
표시 → diff 산출(대시보드 렌더링) → **gate는 무조건 draft로 리셋, revision+1 —
재확정 게이트를 다시 거친다.** 확정(confirmed) 상태에서 재매핑해도 동일하다.

## 산출물 저장 위치

프로젝트 폴더 하위 `01_매핑/`에 mapping.json·dashboard.html(모드 B는
Target시트초안.xlsx 포함)을 쌍으로 저장한다.

## 자주 발생하는 상황

| 상황 | 대응 |
|---|---|
| Target 시트 0개 / 2개 이상 | PAUSE — 모드 B 제안 / 시트 선택 요청 (자동 진행 금지) |
| 체크리스트만 주고 폴더 미지정 | PAUSE — 산출물 폴더 위치를 질의 (폴더 없이 진행 불가) |
| 파일은 있는데 0바이트·손상·포맷 위장 | [결함 증거] → SUSPECT → 조치 필요 목록 + ai_assessment |
| 파일명은 맞는데 표지 제목이 다른 문서 | identity 불일치 → SUSPECT + ai_assessment(근거·확인 위치) |
| 암호 보호·표지 없음·스캔본 | [확인 불가] → **UNVERIFIED** — 불일치 단정 금지, 사람 확인 목록으로 |
| 시트에 없는 표준 산출물이 폴더에 존재 | UNCLAIMED(U-id) + link_reason + scope_gap_candidate — 범위 보완은 사람 결정 |
| 절차그룹명이 표준 12종·별칭에 없음 | UNKNOWN_PROCEDURE_GROUP 경고 + process=null (추측 배정 금지) |
| Target 시트 No. 중복 | DUPLICATE_ITEM_NO(FATAL) — 중복 행 제시, 시트 정비 요청 (자동 재부여 금지) |
| 모드 B 폴더 안에 체크리스트 존재 | CHECKLIST_FOUND_IN_FOLDER(PAUSE) — 모드 A 역제안, 사용자 선택 |
| 모드 B 초안을 검수 없이 모드 A에 입력 | AI_DRAFT_CHECKLIST 정지 — 검수 확인 후 draft_origin 기록하고 진행 |
| listing 모드라 실파일 미접근 | INTEGRITY_NOT_CHECKED 경고 — 매칭 파일 stage 후 --file-root로 재실행 |
| 스캔 후 폴더가 또 바뀜 | SNAPSHOT_DRIFT 경고 — 재스캔(재매핑) 권고 |
| 확정 후 폴더 갱신·재매핑 | --prev로 재실행 — 불변 파일 확정 승계, 변경분 재확인 목록, gate 리셋 |

## references 라우팅

| 파일 | 언제 읽나 |
|---|---|
| `references/target_sheet.md` | 파싱 실패·시트 구조·식별 규칙 의문 시 |
| `references/matching_rules.md` | 상태·SUSPECT·link_reason 규칙 설명 필요 시 |
| `references/oii_map.md` | OII·별칭·키워드 사전 근거 확인 시 |
| `references/folder_inference.md` | 모드 B 진입 전 (필수) |
| `references/ai_assessment.md` | ⑤ AI 단계·정체성 확인 전 (필수) |
| `references/output_contract.md` | 스키마·오류 코드·계약 질문 시 |
