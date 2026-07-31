# 유지보수 가이드 — "어디만 고치면 되나"

이 스킬은 한 곳에 모았지만 내부가 모듈로 나뉘어 있어, 변경이 생겨도 연쇄 수정이 일어나지 않는다. 상황별로 손댈 파일이 정해져 있다.

## 상황별 수정 위치

| 바뀐 것 | 고칠 곳 | 비고 |
| --- | --- | --- |
| 체크리스트 양식(열 추가/삭제, 시트명/단계 변경) | `scripts/config.py` 한 곳 | 모든 스크립트가 여기서 시트·컬럼을 읽음. 다른 코드 불변 |
| 판정 기준(자동 Pass 금지 키워드, 미대상 패턴, Pass 코멘트 문구) | `scripts/classification_rules.py` | `HUMAN_REQUIRED`/`NA_KEYWORDS`/`judge()` |
| 프로젝트가 바뀜(다른 차종·아이템) | `deliverable_map.json`(데이터) 새로 생성 | 코드 불변. 내용 기반으로 AI가 생성 |
| 새 시스템 연동(codebeamer·git) | `scripts/connectors/`에 redmine 패턴 복제 | 기존 파일 불변 |
| 추적성 export 형식이 바뀜 | `scripts/trace_checker.py`의 컬럼 가정 | 소스 col≤3, 타깃 col5, '--'=미연결 |
| 전체 흐름 파악 | `SKILL.md` 한 장 | 목차·트리거·0~5단계 |

## 스크립트별 단일 책임

- `summarize_folder.py` — 폴더 내용 다이제스트(매핑 입력)
- `make_blank_template.py` — 완성본 → 빈 양식(답 칸만 비움)
- `fill_checklist.py` — 매핑+규칙으로 1차 판정 채우기 + 정합성 점검 + 안내 시트
- `coverage_check.py` — 매핑 누락 파일 점검
- `trace_checker.py` / `apply_trace_evidence.py` — 추적성 미연결 집계 → 체크리스트 반영
- `verify_against_baseline.py` — 사람 작성본 대비 검증표
- `config.py` — 시트·컬럼 정의(모두 공유). `classification_rules.py` — 판정 규칙

각 스크립트는 입력/출력이 명확한 CLI라 따로 실행·테스트할 수 있다.

## 전형적 변경 시나리오

1. **양식 개정(Template History 개정번호 증가)**: `template_version.py`가 NEWER 판정 → `make_blank_template.py`로 새 빈 양식 생성 → 출력의 "문항 칸" 검증 줄 확인(컬럼은 머리글 자동 감지, 특이 양식만 `config.py` 폴백 조정) → `assets/latest_template.xlsx` 교체 + `assets/template_version.json` 갱신 → `.skill` 재패키징 후 Save skill 재설치.
2. **새 단계(다음 차수) 점검**: 한 워크북에 차수 시트를 누적하는 증분 모드를 쓴다 — `make_blank_template.py --new-sheet "..." --copy-from "..."`로 직전 차수 시트를 복사해 새 시트만 비우고, 이후 스크립트들은 `--sheet`로 그 시트만 처리한다(기존 완료 시트는 보존 = 직전 차수 스코핑 근거). `config.find_sheets()`는 종류별 시트 '전부'를 리스트로 반환하고, 컬럼은 `config.detect_cols()`가 시트별 머리글로 감지한다(Applicable 없는 구버전 레이아웃 포함). `classification_rules.NA_KEYWORDS`에서 해당 차수에 빼야 할 항목 조정.
3. **일치율이 떨어짐**: 검증표의 위험오판/AI누락을 보고 `classification_rules.py` 또는 `deliverable_map.json`만 손봄. 2단계 재실행 → 검증표로 변화 확인.

## 정직성 불변식 (변경해도 깨지면 안 됨)

- 모든 자동 판정에 `(AI 1차)` 표기 + 안내 시트.
- 일관성·추적성·승인·시스템 근거 항목은 자동 Pass 금지(`확인 필요`).
- 임의 Fail 금지(근거 없는 Fail 금지). 추적성 갭은 "Fail 후보"까지만.
