# AI 1차 판정(ai_assessment) 작성 규칙

4단계(AI 판단)에서 mapping.json을 편집할 때 따르는 규칙. 이 규칙은 VDA
가이드라인의 원칙(기계적 판정 금지, 최종 판정은 어세서 책임)을 스킬 수준에서
구현한 것이다 — 우회하지 않는다.

## 작성 대상 (v0.4)

`item_status`가 **MISSING / VERSION_MISMATCH / SYSTEM_URL / PARTIAL / SUSPECT /
UNVERIFIED** 인 점검 대상 항목 전부. MATCHED·EXCLUDED에는 쓰지 않는다
(불필요한 판정 생성 금지).

## 형식 (필드별)

```json
"ai_assessment": {
  "proposal": "한 문장 제안 — 아래 어휘만 사용",
  "basis": "근거 인용 — 시트 셀 원문, 폴더 부재/존재 사실, 후보 파일명",
  "where_to_look": "점검자가 확인할 곳 — 폴더/시스템/담당자 등 구체적으로",
  "decided_by": "미확정",
  "human_decision": null,
  "human_note": null
}
```

## proposal 어휘 (이것만 사용)

| 상황 | 제안 문구 틀 |
|---|---|
| MISSING | "산출물 미비 가능성 — 폴더 기준. 실제 미작성인지 미제출인지 확인 필요" |
| VERSION_MISMATCH | "버전 확인 필요 — 시트 기재 {A}, 폴더 보유 {B}. 최신본 기준 재지정 권고" |
| SYSTEM_URL | "시스템 직접 확인 필요 — 오프라인 점검 불가. export 사본 확보 권고" |
| PARTIAL | "일부 파일만 확인됨 — 미확인 엔트리: {목록}. 어디를 봐야 하는지 병기" |
| SUSPECT | "매칭 의심 — 불일치 근거: {integrity 코드 또는 identity 근거}. 확인 위치 병기" |
| UNVERIFIED | "확인 불가 — 사유: {암호 보호/표지 없음/파일 미접근}. 사람이 확인할 사항 병기 — 불일치로 단정하지 않음" |

## 금지 사항

1. **"Fail", "부적합", "미수행" 단정 금지.** 폴더에 없다는 사실은 "폴더에
   없다"까지만 말해준다. 사내 시스템에 있거나 미제출일 수 있다.
2. **근거 없는 추정 금지.** basis에 쓸 수 있는 것은 관찰 가능한 사실뿐이다:
   시트 셀 원문, 폴더 스캔 결과, 파일명·버전 토큰. "아마 ~일 것" 류의 추정을
   basis에 넣지 않는다.
3. **decided_by는 항상 "미확정"으로 시작한다.** 사용자가 게이트에서 결정하면
   human_decision에 기록되고, 그때도 decided_by는 사용자 이름으로 바뀐다 —
   AI가 스스로 확정 상태로 바꾸는 일은 없다.
4. **candidates 승격 기준**: fuzzy 후보를 MATCHED로 승격하는 것은 파일명
   구성요소(프로젝트명·산출물명·버전)가 실질 동일하고 표기만 다를 때만.
   산출물명 자체가 다른 파일을 "비슷하니까" 매칭하지 않는다. 확신이 없으면
   candidates에 남겨두고 proposal에 후보 존재를 언급한다.

## unclaimed_files 분류

| classification | 기준 |
|---|---|
| 구버전 | 매칭된 파일의 하위 버전 (예: v0.1이 있고 v1.0이 매칭됨) |
| 검토본 | 파일명에 검토자 표기("김미연 검토" 등) 또는 review 사본 성격 |
| 참고자료 | 점검 대상은 아니나 이후 단계 점검에 활용 가능 (추적성 export, 표준 문서 등) — ai_note에 활용처 기록 |
| 미분류 | 성격 판단 불가 — 사용자 확인 목록에 포함 |

분류에도 basis(파일명 근거)를 한 줄 남긴다.

## AI 파일 열람 공통 규칙 (v0.4: 열람 게이트 모드 공용)

- **열람 게이트 (⑤-b0 / B4)**: 모드 불문, 파일 열람 전에 **열람 대상 건수를
  사용자에게 보고하고 진행 확인**을 받는다 — 무단 대량 열람 금지. 대상이
  과다하면 절차그룹 단위 분할 진행을 제안한다. (모드 A: MATCHED·VERSION_MISMATCH
  evidence / 모드 B: INFERRED_LOW·UNCLASSIFIED)
- 열람 목적은 **무결성 보조 확인·정체성 확인·분류**에 한정한다. 내용 적정성에
  대한 어떤 판단·코멘트도 생성하지 않는다 (2·3단계 몫).
- 열람 범위는 표지·제목·머리말·목차·개정이력·서두 수준까지만.
- PASSWORD_PROTECTED 등 integrity 비정상 파일은 열람을 생략하고 사유를 기록한다.

## 정체성 확인(identity) 규칙

- 대상: status가 MATCHED·VERSION_MISMATCH(해소 후보 포함)인 evidence 전수 —
  **소속 item_status 무관** (PARTIAL 항목 안의 매칭 evidence 포함).
- 판단 어휘 3값만: `일치` / `불일치` / `판단 불가`. 다른 표현 금지.
- 근거 인용 필수 — 예: "표지 제목 'SW 아키텍처 설계서', 프로젝트명 JX1 — 1p".
- `판단 불가`(표지 없음·스캔본 등)는 불일치로 단정하지 않는다 → UNVERIFIED 경로.
- decided_by는 "미확정"으로 시작 — 사람이 게이트에서 정정하면 **result 자체를
  갱신**하고 decided_by를 확정 주체로, human_decision에 정정 내용을 기록한다
  (파생 로직은 항상 result만 읽는다).
- identity 확인은 objective evidence의 유효성 확인이다. content_verified를
  바꾸지 않는다.
- identity 기입 후 **반드시 `python scripts/derive_status.py mapping.json`으로
  item_status를 재파생**한다 — AI가 item_status를 손으로 고치지 않는다.

## v0.4 추가 — 형식별 정체성 앵커

| 형식 | 확인 앵커 | 비고 |
|---|---|---|
| .docx/.doc | 표지 제목·프로젝트명·머리말·개정이력 표 | 1~2쪽 수준 |
| .xlsx/.xls | 시트명 구성·첫 시트 제목행(A1 부근)·개정이력 시트 | 셀 값 나열 금지 — 제목 수준만 |
| .pptx/.ppt | 1쪽(표지 슬라이드) 제목·프로젝트명 | |
| .pdf | 1쪽 제목·머리말 | 텍스트 추출 불가(스캔본)면 "판단 불가" |
| 스캔본·표지 없음 | — | "판단 불가" — 추정 금지, 사람 확인 목록으로 |
