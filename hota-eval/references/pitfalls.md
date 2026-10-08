# 실기 함정과 대응

| # | 함정 | 실제 사례 | 대응 (도구) |
|---|---|---|---|
| 1 | 서명 뒤 APP 재빌드 → 이미지 달라짐 | V3.0.29: Jenkins #32 → #33 → #34, CURRENT 복귀 #35 의 26810 `.s19` 가 서명본과 다름 (Os 태스크 스택 배치, `Os_Cfg.c` 8줄) | identify 가 hash xml 과 빌드 산출물 SHA-256 을 맞춰 보고 다르면 멈춤. 평가·PR 은 서명한 빌드 커밋(`--ref`) 기준 |
| 2 | aSIMS 수령 이름이 제각각 | `_v26810`, `_26810_Test`, `test_..._v26820` | 이름으로 판단하지 않고 hash 로 변형 판별, 결과 폴더에는 수령 이름 그대로 |
| 3 | APP 를 뱅크 A 에만 씀 | 10-02 H-OTA `E_NOTMATCHED_DESTINATION` — B 뱅크에 옛 버전 | 라이팅은 항상 `--banks AB`, 검증 지점 + 다른 뱅크 4곳 일치 확인 |
| 4 | 파일 이름 실수 | v3.0.26 `_BGRules.asc.asc`, v3.0.29 `…_ExternalRule` (s 빠짐) | prepare 가 경로를 만들어 넣음, names·collect 가 규칙 밖 이름을 알림 |
| 5 | BG 와 Repro 를 한 파일로 | Repro 전에 Report Config 를 안 바꾸면 BG 파일에 이어 쓰임 | Rules 마다 prepare (`A3:BGRules`, `A3:ReproRules`) |
| 6 | OEUK 체크 상태 | B2 체크 → B3 해제 → B4 체크 | prepare 가 매번 상태를 보여 줌 (설정 파일 값은 oeuk_off 확인 전까지 화면에서 직접) |
| 7 | 다운그레이드 차단 뒤 APP 지워짐 | A2 · B2 뒤 다음 하위그룹 전 다시 라이팅 필요 | collect 가 `reflash_after` 케이스에서 다시 라이팅 명령을 안내 |
| 8 | 디버거가 붙은 채 시험 | 리셋·FBL 진입이 실제와 다를 수 있음 | 라이팅 직후 분리 확인을 받고 진행 |
| 9 | H-OTA 로그인 만료 | 1주일마다 로그아웃 — 롬패키지·Rules 실패 | E0 에서 확인 |
| 10 | H-OTA 설정 파일 권한 | `C:\ProgramData\GIT\H-OTA Studio\*.ini` 는 일반 터미널에서 쓰기 불가 | 관리자 PowerShell 에서 claude 실행 (prepare 가 백업 후 직접). 아니면 클립보드 모드 |
| 11 | H-OTA `.asc` 로 CAN 출력 판단 | 진단 ID 3개만 기록됨 | CAN 출력은 joule-bench(받기 전용 아님, 레스트버스) 또는 Joule 트레이스로 |
| 12 | 그림 비교 | Excel 이 png 를 재압축 → md5 불일치 | 레포트 검증은 첨부(Ole10Native) 바이트만 |
