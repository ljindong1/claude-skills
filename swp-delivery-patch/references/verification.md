# 검증 — 빌드 검수와 실기

## 1. 빌드 검수 (S10)

| 항목 | 기준 | 도구 |
|---|---|---|
| 빌드 결과 | SUCCESS, 산출물 이름이 새 SWP 버전 | jenkins_wait.py |
| 생성기 | Error 0. Warning 은 직전과 비교해 늘었으면 내용 확인 | jenkins_wait.py |
| Rte Validation | errors 0, warnings 수가 직전 전체 생성 빌드와 같거나 설명 가능 | jenkins_wait.py --compare |
| SAFERTE | SAFERTE_ERR 0, WARN 종류별 건수 증감 설명 가능 | jenkins_wait.py --compare |
| 모듈 신규 Validation | IM 의 신규 ERR 코드가 로그에 없음 | 로그 grep |
| 생성물 diff | 직전 버전 대비 Generated C/H/ARXML 변화가 판정표로 설명됨 | gen_diff_review.py |
| 메모리 | RAM/ROM 증감과 원인 섹션. 직전 값이 같은 방식으로 재현되는지 먼저 확인 | map_mem.py |
| .ver 잔존 | 교체 모듈의 구버전 .ver/.jar 가 남지 않음 | `find -name "*.ver"` |

생성물 diff 해석:
- 바뀌어도 정상인 것: 생성 시각, UUID, Os 스택 배치 순서(크기 동일), 모듈 업데이트로 인한 새 구조체 멤버·표기 변경(`X` → `&X`).
- 설명이 필요한 것: 당사 설정을 바꾸지 않았는데 값이 바뀐 생성 코드, 설정을 바꿨는데 바뀌지 않은 생성 코드(예: 인덱스만 당겨 호출 순서가 같으면 정상).

## 2. 실기 (S12)

순서와 판정 기준만 둔다. 실행은 각 스킬과 프로젝트 체크리스트(프로필 링크)를 따른다.

| 순서 | 내용 | 판정 기준 | 담당 |
|---|---|---|---|
| 1 | ALL 빌드 산출물 4벌 확인 | 네 폴더 모두 새 버전, rom zip 4개 | — |
| 2 | 라이팅 | FBL 짝 자동 선택, **APP 양 뱅크(A·B) 모두**, 검증 지점 전부 일치 | cvd-project |
| 3 | CAN 출력 | 실패 0, 에러 프레임 0, 주의·정보 건수가 직전 회차와 같음(정보 항목은 사양상 정상인 것만) | can-bench-setup |
| 4 | 진단 회귀 | 세션, 보안접근, 읽기/쓰기, Routine, DTC, Reset, 다운로드 계열이 직전과 같은 응답 | canoe-project-setup / CANoe |
| 5 | 패치 고유 시험 | 수평전개 결함의 **재현 조건**을 그대로 케이스로 (예: TransferData Repeat Block → 긍정 응답, HF 이전엔 NRC 0x71). 기능 추가면 그 기능 동작(예: DataLog DID 64B) | CANoe CAPL |
| 6 | 서명 | rom zip 4개 → 서명 요청 → 서명 bin 4개 | 프로필 담당 |
| 7 | H-OTA | 그룹 A(양산 키): 업 성공 / 다운 차단(NRC 0xF4). 그룹 B(TEST): 업 성공 / OEUK 강제 다운 성공. External·BG→Repro 각각. **대칭성**이 판정 | 프로필 체크리스트 |
| 8 | 결과 정리 | 결과 폴더, 보고서 첨부·화면 이번 회차로 교체, 분류별 압축 첨부 | — |
| 9 | CURRENT 복귀 | 지시 시 커밋 | — |

주의:
- 진단 사양서(CDD)가 실제 제어기와 다른 경우가 있다(프로필 확인). 진단 결과를 사양 적합으로 단정하지 않는다.
- 한쪽 뱅크만 쓰면 다른 뱅크로 부팅해 E_NOTMATCHED_DESTINATION 이 난다.
- 실험대에 다른 노드가 없으면 리셋 중 레스트버스 송신이 ACK 없이 막힐 수 있다(리셋 동안 1초 멈춤으로 해결). 실차에는 없는 현상이므로 결과에 실험대 특이사항으로 적는다.
- 보드에 들어간 이미지가 이번 회차인지는 SW 버전 DID 로는 구별되지 않을 수 있다(버전 고정). 해시 DID(예: F1C1 SHA-256)를 서명 해시와 대조한다.

## 3. 결과 파일 규칙

- 결과 폴더: `References/Doc_MB/04_Reprogramming/v<SWP>/<YYMMDD>/` (프로필).
- H-OTA 로그 이름: `{양산|Test}_<제어기>_{Upgrade|DGPrevent|OEUK_DG}(v시작_v목표)_{ExternalRules|BGRules|ReproRules}.asc` — 평가 담당 부서가 파일명만 보고 케이스를 판단한다. 확장자 중복(`.asc.asc`)을 확인한다.
- `.asc` / `.log` / `.png` 는 같은 이름으로 짝을 맞춘다.
- 보고서(보드평가레포트)는 이전 회차 첨부·화면이 남지 않게 이번 회차 파일로 교체한다.
- Redmine 첨부: `<차종>_<제어기>_v<SWP>_<YYMMDD>_{HOTA_asc|HOTA_log|HOTA_png|aSIMS_bin|CAN_bench|<고유시험>|report_xlsx}.zip` 처럼 분류별 압축.
