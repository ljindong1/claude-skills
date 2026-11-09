# 검증 — 정적 검수 · 빌드 검수 · 실기

**들어가기 전** — 적용이 끝나고 판정표의 모든 행이 닫혀 있어야 한다. 검수는 판정표를 기준으로 하는 일이다.
**끝났다고 말하려면** — 각 장의 기준 항목마다 결과(값·건수)와 판정이 있고, 하지 않은 항목은 "미수행"으로 적혀 있어야 한다. 빌드 성공은 실기 검증이 아니고, 정적 검수는 동작 검증이 아니다.

## 1. 정적 검수 (빌드 전)

빌드는 수십 분이 걸리고 push 가 필요하다. 여기서 잡을 수 있는 것은 잡는다. C Studio Generate 는 BSW·Os·Rte 만 만들고 MCAL 은 Jenkins 에서만 돈다(`jenkins-flow.md` §3-1).

먼저 한 번에 돌린다.

```
python scripts/review_all.py --prev … --cur … --app … --old-token … --new-token … --expect … --out 검수보고서.md
```

설정 재대조(`three_way.py --check`), 모듈 바이트 일치, 심볼·매크로(`symbol_crosscheck.py` — Prev 가 있는 배포본에서만), 버전 잔존, 의존 `.ver` 목록, 뺀 모듈의 남은 생성물(`gen_stale_check.py`)을 한 보고서로 낸다. 보고서의 '확인'은 오류가 아니라 사람이 사유를 맞춰 볼 항목이다.

이어서 네 가지를 본다.

**① 재대조 남은 항목** — 전부 판정표의 제외·보류·당사 구성 사유와 **1:1** 인지. 사유 없는 항목은 누락이다.

**② 참조 끊김** — 모듈·인스턴스를 빼거나 ShortName 을 바꾼 패치는 모델 참조가 끊긴 채 남을 수 있다. 손으로 `git grep` 하는 대신 C Studio CLI Validation 으로 기계적으로 본다.

```
mobilgene-cli.exe -nosplash -data <빈 폴더> -consolelog -project <프로젝트 복사본>                   -validation <저장 폴더> -AgreeTermsEarlyCLI y
grep 'line="Configuration/Ecu'    <저장 폴더>/validation-results.xml
grep 'line="Configuration/System' <저장 폴더>/validation-results.xml
```

- **전체 건수는 보지 않는다.** 결과의 대부분은 벤더 정의 파일(`Configuration/Definition`, `Static_Code/Modules`)의 잡음이다 — 실측(2026-11-09, R13.0.0) 1197건 중 당사 설정(`Configuration/Ecu`)은 2건이었다.
- 볼 것은 위 두 경로의 `unresolved proxy` 줄이다. 그것이 끊긴 참조다.
- **이것은 모델/스키마 검증이고 생성기 Validation(`ERR05…`)이 아니다.** 결과에 `ERR05` 코드는 나오지 않는다. 둘을 섞지 않는다.
- 프로젝트를 저장하므로 **복사본에서** 돌린다(`apply.md` §1).
- 도구가 없거나 돌릴 수 없으면 `git grep` 으로 지운 이름을 전수 검색하고, 그렇게 했다고 적는다.

**③ 신규 Validation 사전 점검** — 이번 패치로 새로 생기는 ERR 규칙을 당사 Ecud 에 미리 대 본다(`three-way-merge.md` §7).

**④ 보호 설정** — `protected_check.py … --before-rev <작업 시작 커밋>` 으로 확인 필요 0 이거나 판정표 결정과 1:1.

결과를 요약하고 커밋 지시를 기다린다.

## 2. 빌드 검수

커밋·push 한 뒤 순서는 이렇다. **push 가 빌드 트리거**이므로 커밋은 사용자 지시가 있을 때만 한다.

1. **빌드가 시작됐는지** — Job 이름은 프로필. 번호는 생략하면 최신 빌드를 본다.
2. **끝날 때까지 기다리며 로그를 요약** — `python scripts/jenkins_wait.py <job> [번호] --compare <직전 전체 재생성 빌드>`. 증분 빌드와 비교하면 의미가 없다. 오래 걸리면 백그라운드로 돌리고 완료 알림을 기다린다(폴링 금지).
3. **실패면 거기서 멈춘다** — 로그의 **첫 에러**부터 원인을 찾고, **고치기 전에 원인 분석을 보인다**. 일감에는 오류 코멘트를 올린다(`issue-report.md` §3).
4. **성공이면 Jenkins `Auto commit` 을 pull 한 뒤** 아래 표를 본다 — 생성물은 그 커밋에 들어 있다. 사람 커밋 뒤에는 항상 pull 이 필요하다(`jenkins-flow.md` §1).
5. 결과를 요약해 보고하고, 모든 항목이 설명되면 그 단계의 일감 본문 체크를 닫는다.

| 항목 | 기준 | 도구 |
|---|---|---|
| 빌드 결과 | SUCCESS, 산출물 이름이 새 SWP 버전 | jenkins_wait.py |
| 생성기 | Error 0. Warning 은 직전과 비교해 늘었으면 내용 확인 | jenkins_wait.py |
| Rte Validation | errors 0, warnings 수가 직전 전체 생성 빌드와 같거나 설명 가능 | jenkins_wait.py --compare |
| SAFERTE | SAFERTE_ERR 0, WARN 종류별 건수 증감 설명 가능 | jenkins_wait.py --compare |
| 생성기 Validation | 기대한 신규 ERR 코드 목록과 로그가 1:1 (아래) | 로그 grep |
| 생성물 diff | 직전 버전 대비 Generated C/H/ARXML 변화가 판정표로 설명됨 | gen_diff_review.py |
| 메모리 | RAM/ROM 증감과 원인 섹션. 직전 값이 같은 방식으로 재현되는지 먼저 확인 | map_mem.py |
| .ver 잔존 | 교체 모듈의 구버전 .ver/.jar 가 남지 않음 | `find -name "*.ver"` |

**생성기 Validation 대조** — 일감이나 IM 이 "이번 패치로 새로 생기는 ERR 코드" 목록을 주면 빌드 로그와 1:1 로 맞춘다.

```
grep -o 'ERR[0-9]\{6\}' <빌드 로그> | sort | uniq -c | sort -rn
```

- 기대 목록에 있는데 로그에 없는 것 = 당사 설정이 이미 규칙을 만족하거나, 도구가 자동 교정한 것이다. **어느 쪽인지 적는다** — 자동 교정이면 무엇이 바뀌었는지도.
- 기대 목록에 없는데 로그에 있는 것 = 조사 대상.
- 건수만 세고 끝내지 않는다. 직전 회차 로그와 같은 방식으로 비교한다.

생성물 diff 해석:
- 바뀌어도 정상인 것: 생성 시각, UUID, Os 스택 배치 순서(크기 동일), 모듈 업데이트로 인한 새 구조체 멤버·표기 변경(`X` → `&X`).
- 설명이 필요한 것: 당사 설정을 바꾸지 않았는데 값이 바뀐 생성 코드, 설정을 바꿨는데 바뀌지 않은 생성 코드(예: 인덱스만 당겨 호출 순서가 같으면 정상).

## 3. 실기

순서와 판정 기준만 둔다. 실행과 과제별 설정·체크리스트는 각 스킬(cvd-project·can-bench-setup·canoe-project-setup·hota)이 들고 있다. 비교 대상은 직전 회차의 실기 결과 기록이다.

| 순서 | 내용 | 판정 기준 | 담당 |
|---|---|---|---|
| 1 | ALL 빌드 산출물 확인 | 프로필의 변형 목록만큼 산출물이 **모두** 새 버전 (개수·폴더 이름은 프로필) | — |
| 2 | 라이팅 | FBL 짝 자동 선택, **APP 양 뱅크(A·B) 모두**, 검증 지점 전부 일치 | cvd-project |
| 3 | CAN 출력 | 실패 0, 에러 프레임 0, 주의·정보 건수가 직전 회차와 같음(정보 항목은 사양상 정상인 것만) | can-bench-setup |
| 4 | 진단 회귀 | 세션, 보안접근, 읽기/쓰기, Routine, DTC, Reset, 다운로드 계열이 직전과 같은 응답 | canoe-project-setup / CANoe |
| 5 | 패치 고유 시험 | 수평전개 결함의 **재현 조건**을 그대로 케이스로 (예: TransferData Repeat Block → 긍정 응답, HF 이전엔 NRC 0x71). 기능 추가면 그 기능 동작(예: DataLog DID 64B) | CANoe CAPL |
| 6 | 서명 | rom zip 4개 → 서명 요청(플랫폼설계팀 aSIMS) → 서명 bin 4개. **요청한 빌드 번호·커밋을 기록**하고, 이후 실기가 끝날 때까지 APP 재빌드(push) 금지 — 재생성 때 Os 스택 배치가 바뀌어 이미지가 달라짐 | 프로필 담당 |
| 7 | H-OTA | 그룹 A(양산 키): 업 성공 / 다운 차단(NRC 0xF4). 그룹 B(TEST): 업 성공 / OEUK 강제 다운 성공. External·BG→Repro 각각. **대칭성**이 판정 | hota |
| 8 | 결과 정리 | 결과 폴더, 보고서 첨부·화면 이번 회차로 교체, 분류별 압축 첨부 | — |
| 9 | CURRENT 복귀 | 지시 시 커밋 | — |

주의:
- 진단 사양서(CDD)가 실제 제어기와 다른 경우가 있다(프로필 "프로젝트 사실" 확인). 진단 결과를 사양 적합으로 단정하지 않는다.
- 한쪽 뱅크만 쓰면 다른 뱅크로 부팅해 E_NOTMATCHED_DESTINATION 이 난다.
- 실험대에 다른 노드가 없으면 리셋 중 레스트버스 송신이 ACK 없이 막힐 수 있다(리셋 동안 1초 멈춤으로 해결). 실차에는 없는 현상이므로 결과에 실험대 특이사항으로 적는다.
- 보드에 들어간 이미지가 이번 회차인지는 SW 버전 DID 로는 구별되지 않을 수 있다(버전 고정). 해시 DID(예: F1C1 SHA-256)를 서명 해시와 대조한다.

## 4. 결과 파일 규칙

- 결과 폴더: 저장소의 Reprogramming 폴더 아래 `v<SWP>/<YYMMDD>/`. 폴더 이름은 과제마다 다르므로 프로필에 적고, 직전 회차와 같은 자리에 둔다.
- H-OTA 로그 이름: `{양산|Test}_<제어기>_{Upgrade|DGPrevent|OEUK_DG}(v시작_v목표)_{ExternalRules|BGRules|ReproRules}.asc` — 평가 담당 부서가 파일명만 보고 케이스를 판단한다. 확장자 중복(`.asc.asc`)을 확인한다.
- `.asc` / `.log` / `.png` 는 같은 이름으로 짝을 맞춘다.
- 보고서(보드평가레포트)는 이전 회차 첨부·화면이 남지 않게 이번 회차 파일로 교체한다.
- Redmine 첨부: `<차종>_<제어기>_v<SWP>_<YYMMDD>_{HOTA_asc|HOTA_log|HOTA_png|aSIMS_bin|CAN_bench|<고유시험>|report_xlsx}.zip` 처럼 분류별 압축.
