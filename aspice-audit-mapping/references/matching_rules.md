# 매칭 규칙과 상태 정의 (정본)

## 정규화 (norm)

시트 기재 파일명과 폴더 파일명 양쪽에 동일 적용:

1. 유니코드 NFC 정규화 (한글 자소 분리 대응 — macOS/Windows 혼용 폴더 필수)
2. 확장자 제거 (`.xlsx .xls .docx .doc .pdf .zip .eml` 등)
3. 공백·기호 제거: 공백, `_`, `-`, `[`, `]`, `(`, `)` → 삭제
4. 소문자화

## 버전 토큰

정규화 전 원문에서 `v1.0`, `V1.1`, `Rev02`, `R43`, `_260609`(날짜) 패턴을
버전 토큰으로 분리해 `base`(버전 제외 정규화명)와 `version`을 얻는다.
버전 표기가 없으면 version=None.

## 엔트리 상태 판별 순서 (엔트리 = 시트 셀의 파일명/URL 1건)

```
1. http(s):// 시작            → SYSTEM_URL
2. norm 완전 일치              → MATCHED
3. norm 부분 포함(양방향)       → MATCHED (resolved_path에 실제 파일 기록)
4. base 일치·version 상이      → VERSION_MISMATCH (version_note에 양쪽 버전,
                                 candidates에 폴더 후보 전부)
5. base 부분 유사(문자 겹침률
   기반 후보 존재)             → 상태는 MISSING 유지 + candidates에 후보 기록
                                 (AI가 4단계에서 확정해야만 MATCHED로 승격)
6. 그 외                      → MISSING
```

## 항목 상태 파생 우선순위표 (item_status — v0.4 정본, 첫 일치 규칙 적용)

구현 정본은 `scripts/derive_status.py` — 아래 표와 항상 일치해야 한다.
⑤(AI 정체성 확인) 이후에는 `python scripts/derive_status.py mapping.json`으로
**재파생**한다 (④의 값은 잠정치).

| 순서 | 조건 | item_status |
|---|---|---|
| 0 | target=false (비고 [점검 미대상]) | EXCLUDED |
| 1 | evidence 중 **[결함 증거]** 존재 — identity "불일치" / FILE_EMPTY / FILE_CORRUPT / FORMAT_MISMATCH | SUSPECT |
| 2 | (1 아님) **[확인 불가]** 존재 — PASSWORD_PROTECTED / NOT_CHECKED / identity "판단 불가" | UNVERIFIED |
| 3 | MISSING과 비-MISSING 엔트리 혼재 | PARTIAL |
| 4 | 전부 MISSING (파일명 미기입 포함) | MISSING |
| 5 | VERSION_MISMATCH 존재 | VERSION_MISMATCH |
| 6 | SYSTEM_URL 존재 (나머지 전부 MATCHED·정상) | SYSTEM_URL |
| 7 | 전부 MATCHED (identity 미기록은 잠정 MATCHED — ⑤ 후 재파생) | MATCHED |

**SUSPECT vs UNVERIFIED (v0.4 분리)**: "틀렸다는 증거가 있음"(SUSPECT)과
"확인하지 못함"(UNVERIFIED)은 다른 범주다. 암호 보호·표지 없는 스캔본을
'매칭 의심'으로 단정하는 것은 근거 없는 부정 판정이다 (프로젝트 지침 4절,
ISO 33002 data validation 관점 — 해석 여지 있음). NOT_CHECKED(파일 미접근)도
[확인 불가]이며, stage 후 재실행으로 해소하는 것이 표준 절차다.

혼재 시 정보 손실 금지 — item_status가 무엇이든 엔트리별 상태는 보존한다.

## 중복 claim 규칙 (v0.4 — 1파일 N행)

같은 문서가 여러 행에 기재될 수 있다(예: 추적성 자료가 SWE.2·SWE.3 양쪽 행에).

- **1파일 → N항목 매칭을 허용**한다. 각 행의 evidence는 독립적으로 판정된다.
- 한 곳이라도 claim된 파일은 UNCLAIMED가 아니다.
- summary 집계는 **항목(evidence) 기준**이므로 파일 수와 다를 수 있다 —
  대시보드에 이 주석을 유지한다.

## SYSTEM_URL 판별 규칙 (v0.4 명문화)

기재 값이 `http://`/`https://`로 시작하면 SYSTEM_URL. 사내 시스템 도메인 목록은
`scripts/config.py`에 두고 필요 시 확장한다 (하드코딩 금지 원칙 내 상수 관리).
SYSTEM_URL evidence는 **integrity·identity를 검사하지 않는다**(null 고정) —
수동 확인 대상이며 자동 Pass 금지 영역이다.

## 스캔 제외 규칙

- `~$*` (Office 임시파일), `.tmp`, `Thumbs.db`, `.lnk`
- `_` 로 시작하는 디렉터리 (작업 폴더 관례)
- 숨김 폴더(`.git` 등)

## 상태 의미에 대한 주의 (표준 근거)

- **MATCHED는 존재 확인일 뿐이다.** BP/practice 수행과 outcome 달성의 증거가
  아니다 (PAM 4.0 측정 프레임워크 관점 — 존재성 ≠ 수행). 대시보드·리포트에
  "내용 적정성 미검증" 표기를 유지한다.
- **SYSTEM_URL은 자동 Pass 금지 영역.** 사내 시스템(PMS·Redmine·Git) 근거는
  export 사본 또는 점검자 직접 확인으로만 판정 가능하다.
- **VERSION_MISMATCH는 어느 쪽이 옳은지 단정하지 않는다.** 시트가 구버전을
  기재했을 수도, 폴더에 최신본이 누락됐을 수도 있다 — 양쪽 버전을 병기하고
  사용자 확인으로 넘긴다.
- **UNCLAIMED(폴더에만 있는 파일)는 결함이 아니다.** 구버전·검토본·참고자료일
  수 있으며 성격 분류만 한다. 단, 추적성 export처럼 이후 단계 점검에 쓸 가치가
  있는 파일은 ai_note에 활용 후보로 표시해 둔다.

## v0.3 추가 — 매칭 검증 계층

### match_basis 3종

| 값 | 의미 |
|---|---|
| exact | 원문 파일명 완전 일치 |
| normalized | 정규화(NFC·기호·확장자 무시) 후 일치/포함 |
| fuzzy_ai | fuzzy 후보를 AI가 확정 제안 — decided_by 기록, 게이트 검토 목록 대상 |

동일 파일명이 복수 경로에 존재하면 자동 채택하지 않고 candidates에 나열한다
(확정은 AI 제안 + 사용자 게이트).

### 무결성 코드 (verify_matched_files.py — 결정론)

| integrity | 판별 |
|---|---|
| OK | 정상 열림 (zip 서명·포맷 검사 통과) |
| FILE_EMPTY | 0바이트 또는 실질 내용 없음 |
| FILE_CORRUPT | 열기 실패·구조 손상 |
| FORMAT_MISMATCH | 확장자와 실제 포맷 불일치 (매직 바이트 대조) |
| PASSWORD_PROTECTED | 암호 보호로 내용 확인 불가 |
| NOT_CHECKED | 파일 미접근(클라우드 listing 모드 등) — 경고 대상, stage 후 재검사 필요 |

### 무결성 코드 이분류 (v0.4 §4.2 ③′)

| 부류 | 코드 | 파생 결과 |
|---|---|---|
| [결함 증거] | FILE_EMPTY, FILE_CORRUPT, FORMAT_MISMATCH | SUSPECT |
| [확인 불가] | PASSWORD_PROTECTED, NOT_CHECKED | UNVERIFIED |

identity도 같은 이분류를 따른다: "불일치" → [결함 증거], "판단 불가" → [확인 불가].
identity "판단 불가"를 SUSPECT로 강등하지 않는다 (불일치 단정 금지).
파생표 자체는 위 "항목 상태 파생 우선순위표" 절이 정본이다.

### UNCLAIMED link_reason 판별 순서 (결정론)

```
1. 같은 베이스명의 다른 버전이 이미 매칭됨      → VERSION_SUPERSEDED
2. fuzzy 후보로 올랐으나 매칭 미확정·탈락       → REJECTED_CANDIDATE
3. 그 외 (시트 어느 행에도 기재 없음)           → NOT_LISTED
```
