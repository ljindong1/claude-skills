# 보호 설정과 덮어쓰기 점검 — Harmonize·도구·수동 반영 공통

## 목차
1. 왜 따로 점검하나
2. 덮어써지는 세 경로
3. 변경 분류 (a)~(d)
4. 규칙
5. 단계별로 하는 일
6. Harmonize 를 돌릴 때
7. 기록 형식

## 1. 왜 따로 점검하나

패치 후 당사 로직 문제의 대부분은 **당사가 일부러 정한 값이 다른 값으로 바뀌었는데 바꾼 쪽도 검토하는 쪽도 의식하지 못한 경우**였다. 바뀐 Ecud 는 Jenkins 가 다시 생성해 자동 커밋하므로, 설정 단계에서 놓치면 생성 코드까지 조용히 바뀐 채 지나간다.

그 순간에는 "지금 쓰는 곳이 없다", "동작 차이 없다"로 판단되는 경우가 많다. 그런데 그 판단이 틀렸거나, 나중에 그 기능을 쓰게 되면서 문제가 드러났다. 그래서 **보호 설정이 바뀌는 것은 영향 분석 결과와 상관없이 사람이 확인한다.**

사례 (FBL V3.0.19, 2026-10-10 Harmonize 시험, Can·CanIf 만 선택, 옵션 기본값):
- `CanIfMetaDataSupport` 1 → 0 (Overwrite User-Configured 옵션). 쓰는 PDU 는 없었다.
- 0x7AB `CanFdPaddingValue` 없음(생성 0xFF) → 0 명시. CAN FD 송신의 빈 바이트 값이 바뀔 수 있다.
- 진단 수신 `CanHwObjectCount` 10 → 64, 0x7DF 객체 이름 변경, ObjectId·RxPduId 재배정.
- 결과는 VC 견본과 Can/CanIf 기준으로 완전히 같았다 — **VC 견본 = Harmonize 결과물**이다. VC 와 맞추는 것은 곧 Harmonize 로 덮어쓰는 것과 같다.

## 2. 덮어써지는 세 경로

| 경로 | 어떻게 바뀌나 | 놓치기 쉬운 이유 |
|---|---|---|
| Harmonize (C Studio "Generate ECU Configuration", mobilgene CLI) | Overwrite User-Configured / Remove Invalid / Auto-Regeneration of Handle Id 가 **기본으로 켜져 있다** | 바뀐 내역이 git 무시 폴더 `Automation-Results/*.xls` 에만 남는다. 텍스트 diff 는 타임스탬프 잡음에 묻힌다 |
| 이 스킬·사람의 반영 | HAE Cur·VC 를 정답으로 보고 "차이를 맞춘다" | 3-way 에서 VC = 정답이라는 편향. 당사 값의 이유가 저장소에 없는 경우가 많다 |
| 생성기 기본값 | 값이 **없는** 파라미터는 생성기 기본값을 쓴다. 누가 값을 명시하거나 지우면, 또는 모듈 버전이 바뀌어 기본값이 바뀌면 생성 코드가 바뀐다 | 설정 diff 에는 "파라미터 추가"로만 보이거나 아예 안 보인다. 생성 코드 diff 에서만 드러난다 |

## 3. 변경 분류 (a)~(d)

적용·Harmonize 뒤 Ecud 전후 차이를 이렇게 나눈다. three_way.py `--check`, protected_check.py, 의미 비교(타임스탬프·UUID 제외) 결과를 합쳐 본다.

| 분류 | 뜻 | 처리 |
|---|---|---|
| (a) 의도된 변경 | IMS 안내·IM·IA/VC 규칙이 명시한 변경, 3-way "복사 가능" | 판정표 근거대로 |
| (b) **보호 설정 변경** | 프로필 '보호 설정' 표의 값이 바뀜, 또는 키가 없어짐(이름 변경·삭제) | **4장 규칙 — 반드시 사용자 확인** |
| (c) 이름·순서·ID | 컨테이너 이름, ObjectId, Handle ID, 순서만 바뀜 | 손으로 쓴 코드(Application, usercode, Static_Code)가 그 이름·번호를 쓰는지 `git grep` 으로 확인. 쓰면 (b) 로 올린다 |
| (d) **기본값 의존 변화** | 양쪽에 있는 컨테이너 안에서 파라미터가 새로 생기거나 사라짐 | **4장 규칙 — 반드시 사용자 확인**. 생성 코드에서 기본값 → 명시값 차이를 찾는다 |

보호 설정 표에 없는 값이라도 당사 값이 HAE Prev·Cur·VC 와 모두 다르면(3-way "충돌") 보호 후보다. 이유를 찾아 표에 올리자고 제안한다.

## 4. 규칙

1. **(b)·(d) 는 "동작 차이 없음"으로 판단했어도 자동 통과시키지 않는다.** 판정표에 현재 값 / 바뀐 값 / 영향 분석 / 근거를 쓰고 사용자 확인을 받는다. 결정은 둘 중 하나다.
   - 당사 값 유지: 반영 뒤 되돌리고, Harmonize 를 다시 돌리면 또 바뀐다는 것을 판정표·Redmine 에 적는다.
   - HAE 값 채택: 보호 설정 표에서 그 행을 고치거나 지우고, 이유를 적는다.
2. **이유를 모르는 당사 값도 보호 대상이다.** "이유 미상"으로 표에 두고, 바꿀지는 사용자가 정한다. 모른다고 HAE 값으로 맞추지 않는다.
3. **VC·Harmonize 결과와 맞추자는 제안은 보호 설정 표와 먼저 대조한다.** 겹치면 "VC 와 다름 = 당사 의도일 수 있음"으로 표시하고 1 을 따른다.
4. **(d) 는 설정이 아니라 생성 코드로 확인한다.** S10 의 Generated diff 에서 그 파라미터가 쓰이는 값(예: `PaddingValue 255u → 0u`)을 찾아 판정표 행과 잇는다.
5. 새로 확정한 보호 설정은 작업이 끝날 때 프로필 표에 추가한다.

## 5. 단계별로 하는 일

| 단계 | 할 일 |
|---|---|
| S0 | 프로필 '보호 설정' 표가 있는지 본다. 없으면 S6 에서 채울 항목으로 표시 |
| S6 | three_way.py 결과의 "충돌"과 VC/Cur 대비 당사 고유값을 보호 설정 표와 대조. 판정표의 해당 행에 "보호" 표시 |
| S8 (적용·Harmonize 직후) | `protected_check.py --profile … --root <앱> --part FBL|APP --before-rev HEAD` — 커밋 전 작업 폴더를 HEAD 와 비교한다. Harmonize 를 썼으면 6장 절차를 함께 한다 |
| S9 | 위 명령을 다시 돌려 확인 필요 0건이거나, 남은 항목이 모두 판정표 사유와 1:1 인지 본다 |
| S10 | Jenkins 생성 커밋에서 (b)·(d) 에 해당하는 생성 코드 변화를 찾아 설명한다. 설정을 바꾸지 않았는데 생성 코드가 바뀌었으면 기본값 변화(모듈 버전업)를 의심한다 |
| S11 | Redmine 코멘트의 "적용 제외·당사 값 유지" 절에 (b)·(d) 결정을 적는다 |

## 6. Harmonize 를 돌릴 때

1. **시험 브랜치에서 먼저 돌린다**(`test/harmonize_<대상>_<날짜>`, 로컬 전용, push 금지). push 하면 Jenkins 가 빌드하고 자동 커밋한다.
2. **모듈은 꼭 필요한 것만 고른다.** 이 C Studio 버전은 기본 선택이 없다. "Check prerequisite modules automatically"·"Check previous selection" 은 범위를 넓히므로 끈다. 위쪽 "may be selected for prerequisite: EcuC" 는 안내일 뿐이다.
3. 옵션 화면을 캡처해 판정표에 남긴다. 기본값:

   | 옵션 | 기본 | 영향 |
   |---|---|---|
   | Auto-Regeneration of Handle Id | 켬 | PDU Handle ID 재배정 → (c) |
   | Remove Invalid Configurations | 켬 | DB·EcuExtract 와 안 맞는 컨테이너 삭제 → (b) 후보 |
   | Overwrite User-Configured Parameters and References | 켬 | **당사 수동 값 덮어씀** → (b) |
   | Create Json For CLI | 끔 | — |
   | Can: Enable Basic TX CAN greater than | 32 | 송신 메시지 수 기준 BASIC 전환 |
   | CanIf: split routing tx … same Basic CAN | 끔 | — |

   Overwrite 를 끄면 덮어쓰기는 줄지만 HAE 가 의도한 변경도 빠질 수 있다. 미리 보기는 기본값으로 돌려 전체 영향을 보고, 실제 반영 방식은 그 결과를 보고 정한다.
4. 끝나면 바로 `Automation-Results/Automation_<시각>.xls`(git 무시)와 `.log/ODX_<시각>` 을 작업 폴더 밖에 보관하고 읽는다. "value Change from A to B", "Removed Container", "Created Container" 줄이 덮어쓰기 목록이다.
5. `git status`·`git diff --stat`, 의미 비교, `protected_check.py --before-rev HEAD` 로 (a)~(d) 를 나눈다. `.settings/com.autron.odin.auto.config.prefs` 에 선택 모듈·옵션이 기록된다(이전에 누가 무엇을 Harmonize 했는지도 보인다).
6. 채택할 변경만 작업 브랜치에 항목 단위로 옮긴다(decision-rules: Harmonize 부산물 이식 금지). 시험 브랜치는 C Studio 를 **완전히 닫은 뒤** 되돌리고 지운다 — 열린 채로 되돌리면 메모리의 결과를 다시 저장할 수 있다. 다시 열면 F5, 저장 묻으면 "No".

## 7. 기록 형식

판정표 형식은 `three-way-merge.md` §6 하나다. 보호 설정 행 예:

| HAE 요청 | 판정 | 경로 | 이전 상태 (Ours) | 처리 (파일) | 확인 근거 | 이력 (이전 회차) |
|---|---|---|---|---|---|---|
| (Harmonize 부수 변경) CanIfMetaDataSupport | 보호 — 당사 값 유지 | A | 1 (#38061, 이유 미상) | Ecud_CanIf 되돌림 | 쓰는 PDU 0건(CanIf_Cfg.c 전부 INVALID_METADATA_TYPE), 사용자 확인 10-11 | #38061 부터 1, HAE 배포본·VC 는 0 (3.0.18·3.0.19 동일) |

Redmine "적용 제외·당사 값 유지" 절에는 위 행을 그대로 옮기고, Harmonize 를 다시 돌리면 같은 값이 덮어써진다는 것을 한 줄 적는다.
