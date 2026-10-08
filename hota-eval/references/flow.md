# 흐름 세부

근거: HE1i PSU V3.0.26 ~ V3.0.29 평가(#47967 · #48881 · #48909 · #48891), 플랫폼설계팀 가이드 #47967 note-21~23, 체크리스트 Confluence 348160048 · 350453833.

## 케이스 (HE1i PSU, low=26810 · high=26820)

| # | 그룹 | Rules | rom (변형) | OEUK | 기대 | TC |
|---|---|---|---|---|---|---|
| A1 | A (OEUK_HE1I) | External | he1i_high | 해제 | Success, SW high | TC_004 |
| A2 | A | External | he1i_low | 해제 | NRC 0xF4 (차단), SW high 유지 | TC_005 |
| A3 | A | BG → Repro | he1i_high | 해제 | Success / Success | TC_007 |
| A4 | A | BG → Repro | he1i_low | 해제 | Success / NRC 0xF4 | TC_008 |
| B1 | B (OEUK_TEST) | External | test_high | 해제 | Success | (참고) |
| B2 | B | External | test_low | **체크** | Success + 27 13/14, SW low | TC_006 |
| B3 | B | BG → Repro | test_high | 해제 | Success / Success | (참고) |
| B4 | B | BG → Repro | test_low | **체크** | Success / Success + 27 13/14 (Repro) | TC_009 |

판정이 통과하려면 대칭이어야 한다 — A2·A4 가 0xF4 로 막히고 B2·B4 가 성공. 한쪽만 맞으면 통과 아님.

## 보드 상태 전이 (라이팅 시점)

```
CVD low (AB)      → A1 (→high) → A2 (차단, high 유지 · APP 영역 지워짐)
CVD low (AB)      → A3 BG·Repro (→high) → A4 (BG 성공, Repro 차단)
CVD low_test (AB) → B1 (→high) → B2 (OEUK 강제 → low)
CVD low_test (AB) → B3 (→high, OEUK 해제) → B4 (OEUK 체크 → low)
```
각 라이팅 뒤 디버거를 분리한다(붙어 있으면 리셋·FBL 진입이 실제와 다를 수 있다). CANoe·T32 는 꺼 둔다.

## 판정 기준 (judge)

| 항목 | 근거 | 방법 |
|---|---|---|
| 결과 | Output .log | 마지막 `Run active document <rule> success/fail`, `NRC(0xF4)` |
| SW 버전 | Output .log | 마지막 `response SW version : N` |
| 소요 시간 (표시만) | Output .log | External · Repro = 사전 절차 성공 → 결과 줄, BG = `[background-rule Start]` → 결과 줄. 회차 비교는 같은 방식으로만 |
| 27 13/14 | .asc | 프로필 `oeuk_auth` 의 Rules 에서 `27 13`→`67 13`, `27 14`→`67 14` (서비스 바이트 위치만, 데이터 안 우연 일치 제외). BG 는 `27 11/12` 라 대상 아님 |

로그는 한 파일에 여러 실행이 이어 쓰일 수 있어 **마지막 실행**만 본다.

## 결과 폴더

```
04_Reprogramming/v<SWP>/<YYMMDD>/
  <케이스 이름>_<Rules>.asc / .log / .png      12 세트
  aSIMS_enc_signed_..._<변형>.bin               4 (수령 이름 그대로)
  (<차종>)(<제어기>)보드평가레포트_<YYMMDD>.xlsx
```
이전 회차 레포트를 복사해 오면 report 가 템플릿으로 쓴다. 다 바꾼 뒤 옛 날짜 xlsx 는 지운다(사용자 확인).

## 산출물

- 보드평가레포트: 프로필 `[report.ole]` · `[report.picture]` 개체를 같은 위치·크기로 바꾸고 이름 유지. 헤더 FBL/APP 버전·작성일. 첨부는 Ole10Native 를 꺼내 바이트 비교로 검증한다(그림은 Excel 이 재압축하므로 비교하지 않는다).
- TC_001(CAN 출력)은 can-bench-setup 의 joule-bench 실행 폴더(`result.txt`, `B-CAN.asc`, `Local.asc`)를 `--bench` 로 준다.
- Redmine zip: `<prefix>{HOTA_asc, HOTA_log, HOTA_png, aSIMS_bin, report_xlsx, CAN_bench, <하위폴더>}.zip`. Redmine 업로드는 사람이 한다.
- summary 표는 Redmine 결과 코멘트(#48909 · #48891 형식)와 Confluence 체크리스트 "7. 결과 기록"에 그대로 쓴다.
