# 완전 CLI 모드 파일럿

목표: H-OTA Studio 화면의 Start 클릭까지 없앤다. Joule `joule-hota` 는 Updater 를 `-DIRECT <롬패키지> -task <external|background|reprogram> -ViewType CCU1` 로 돌리고, 결과 TCP(9813)와 받기 전용 기록으로 판정한다. 관리자 권한이 필요하다(Studio·Updater manifest `requireAdministrator`) — 관리자 PowerShell 에서 claude 를 실행한다.

## 확인할 것 (A1 한 케이스로)

| # | 질문 | 확인 방법 |
|---|---|---|
| 1 | Updater `-task external` 가 Studio 의 External Rules 와 같은 순서인가 | 받기 전용 `.asc` 를 오늘 A1 `.asc` 와 서비스 순서 비교 |
| 2 | Updater 가 `EditorConfig.ini [TESTREPORT] ReportFilePath` 에 .asc 를 남기는가 | prepare 후 실행, 파일 생김 여부 |
| 3 | `configuration.ini OEUK` 가 OEUK Vehicle 체크와 같은가, 해제 값은 무엇인가 | Studio 화면에서 체크/해제 후 파일 값 비교 → 프로필 `oeuk_off` |
| 4 | 결과 메시지 형식 (Direct 는 Summary Report 경로) | `joule-hota` 결과 로그, PC 설정 `[result]` 정규식 보정 |
| 5 | Rules 에 bin 을 직접 줄 수 있는가, 롬패키지가 꼭 필요한가 | 오늘 GUI 는 bin 직접 지정. Updater 는 롬패키지(`--build`) |
| 6 | 화면 캡처 대신 무엇을 레포트 그림으로 넣을까 | Summary Report / 로그 요약을 그림으로 만들지 사용자와 정한다 |

## Joule 쪽 개선 후보 (Joule 프로젝트에서 판단)

- `joule-hota` reprogram 단계에 `report_file`(Report Config .asc 경로)·`oeuk`(on/off) 항목 — 실행 전 ini 를 바꾸고 끝나면 되돌림
- 시나리오에 A·B 그룹 표준 TC 묶음(A1~B4)과 `prompt` 라이팅 단계 — 지금은 hota-eval 프로필 `[[case]]` 에 있다
- `--bin-only` 에 `--source <s19>` (설정 파일에 패키지를 추가하지 않고 한 번 변환)

파일럿이 끝나면 이 문서와 SKILL.md "완전 CLI 모드"를 실기 결과로 고치고, 흐름 E4·E5 의 사람 단계를 joule-hota 호출로 바꾼다.
