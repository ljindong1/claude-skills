# 완전 CLI 모드 파일럿

목표: H-OTA Studio 화면의 Start 클릭까지 없앤다. Joule `joule-hota` 는 Updater 를 `-DIRECT <롬패키지> -task <external|background|reprogram> -ViewType CCU1` 로 돌리고, 결과 TCP(9813)와 받기 전용 기록으로 판정한다. 관리자 권한이 필요하다(Studio·Updater manifest `requireAdministrator`) — 관리자 PowerShell 에서 claude 를 실행한다.

## 확인할 것 (A1 한 케이스로)

| # | 질문 | 확인 방법 |
|---|---|---|
| 1 | Updater `-task external` 가 Studio 의 External Rules 와 같은 순서인가 | 받기 전용 `.asc` 를 오늘 A1 `.asc` 와 서비스 순서 비교 |
| 2 | Updater 가 `EditorConfig.ini [TESTREPORT] ReportFilePath` 에 .asc 를 남기는가 | prepare 후 실행, 파일 생김 여부 |
| 3 | `configuration.ini OEUK` 가 OEUK Vehicle 체크와 같은가, 해제 값은 무엇인가 | Studio 화면에서 체크/해제 후 파일 값 비교 → 프로필 `oeuk_off` |
| 4 | 결과 메시지 형식 (Direct 는 Summary Report 경로) | `joule-hota` 결과 로그, PC 설정 `[result]` 정규식 보정 |
| 4-1 | CLI 로그(`.log`)를 결과 폴더로 가져올 수 있는가, GUI Output 로그와 형식이 같은가 | 매뉴얼 16장: OBD 는 `롬팩경로\CCU1_OBD_LOG\Reprogram_<시각>.log`, Direct 는 결과 TCP 로 경로 전달. 받은 로그를 `<케이스>_<Rules>.log` 로 복사하고, judge 가 읽는 `Run active document … success/fail` · `response SW version` 줄이 있는지 비교 — 다르면 judge 를 맞춘다. `.log` 를 다른 기록으로 만들어 내지 않는다 (H-OTA 판정 기록) |
| 5 | Rules 에 bin 을 직접 줄 수 있는가, 롬패키지가 꼭 필요한가 | 오늘 GUI 는 bin 직접 지정. Updater 는 롬패키지(`--build`) |
| 6 | 화면 캡처 대신 무엇을 레포트 그림으로 넣을까 | Summary Report / 로그 요약을 그림으로 만들지 사용자와 정한다 |

## Joule 에 필요한 기능 (구현은 Joule 프로젝트에서)

Joule 코드는 이 스킬에서 고치지 않는다. 필요한 기능이 생기면 이 목록에 더하고 사용자에게 전달한다.

### 바로 쓸모 있는 것 (2026-10-08 실기에서 막힌 것)

| # | 대상 | 기능 | 왜 (사례) | 입력 → 출력 |
|---|---|---|---|---|
| 1 | `reprog/uds_client.py` `ReprogUds` | ISO-TP 송신을 실행 기록 트레이스에 남기기 | ISO-TP 가 `CanBase.send` 를 거치지 않아 0x7A3 물리 요청(`10 02`·`11 01` 등)이 `.asc` 에 빠짐 (V3.0.29 P4). P3 는 스크립트에서 TxProxy 로 우회 | 동작 변경 없음 → `.asc` 에 0x7A3 요청 프레임 |
| 2 | `ReprogUds` | 진단 FD 옵션 `can_fd` · `tx_data_length`(64) · `tx_data_min_length`(8) · `bitrate_switch` | APP BG 경로는 요청이 CAN FD 64바이트이고 짧은 요청도 8바이트 채움이 필요. 4바이트 FD 는 ECU 무응답 (V3.0.29 P3 APP). 지금은 클래식 8바이트 고정 | `[reprog]` 에 `fd = true` 등 → FD 송신 |
| 3 | `joule-deep` TC 단계 | 기능 주소(0x7DF) 요청 단계 — 예 `diag_request_functional = "3E 00"`, `expect`, `repeat` · `interval_ms` | `diag_request` 는 물리 주소만이라 0x7DF 기능 요청 시험(V3.0.29 P4)을 별도 스크립트로 함 | 기능 요청 → 0x7AB 응답 수집·판정, 반복 대비 응답 수 |

### 완전 CLI 평가용 (`joule-hota`, 파일럿 뒤 확정)

| # | 기능 | 왜 | 입력 → 출력 |
|---|---|---|---|
| 4 | reprogram 단계 `report_file`(Report Config .asc 경로) · `oeuk`(on/off) | 케이스마다 .asc 이름과 OEUK 체크가 바뀜. 지금은 hota-eval `prepare` 가 H-OTA ini 를 직접 바꿈 | 단계 값 → 실행 전 `EditorConfig.ini` · `configuration.ini` 반영(백업), 끝나면 되돌림 |
| 5 | A·B 그룹 표준 TC 묶음(A1~B4) + 라이팅 `prompt` 단계 | 12회 실행 순서·기대값(Success / 0xF4 / 27 13/14)·하위그룹 전 다시 라이팅을 시나리오 하나로. 지금은 hota-eval 프로필 `[[case]]` | `configs/ota` TC → `result.txt` 케이스별 판정 |
| 6 | `--bin-only --source <s19>` | 회차마다 `configs/ota` 에 패키지 4개(`V29_*`)를 추가하지 않고 서명본을 한 번 변환 | s19 경로 → 같은 이름 `.bin` |

1~3 은 지금 진행해도 되고, 4~6 은 위 "확인할 것"을 A1 한 케이스로 파일럿한 뒤 정한다.

파일럿이 끝나면 이 문서와 SKILL.md "완전 CLI 모드"를 실기 결과로 고치고, 흐름 E4·E5 의 사람 단계를 joule-hota 호출로 바꾼다.
