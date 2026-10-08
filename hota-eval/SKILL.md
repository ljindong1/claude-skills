---
name: hota-eval
description: H-OTA 리프로그래밍 평가(A 그룹 OEUK_HE1I 다운그레이드 차단 · B 그룹 OEUK_TEST 강제 다운그레이드, External · BG→Repro Rules 12회)를 CLI 로 끌고 가는 스킬 — 서명본 4벌 자동 판별(aSIMS hash xml ↔ 빌드 산출물, 서명 뒤 재빌드 감지), bin 배치, 케이스별 Report Config(.asc 이름)·OEUK 준비, 실행 뒤 .log/.asc 로 버전 업·다운 자동 판정(업그레이드 Success · 다운그레이드 NRC 0xF4 차단 · OEUK 강제 다운그레이드 27 13/14 · SW 버전), 파일 이름 규칙 검사, 보드평가레포트 xlsx 첨부·그림·헤더 교체, Redmine 첨부 zip, Redmine/Confluence 결과 표 초안. 사용자가 "H-OTA 평가", "A 그룹 B 그룹", "리프로그래밍 평가", "업그레이드 다운그레이드 평가", "OEUK 강제 다운그레이드", "External Rules / BG Rules / Repro Rules", "Report Config", "보드평가레포트 첨부 바꿔줘", "aSIMS 서명 받았어", "서명본 bin", "26810 26820 평가", "평가 결과 정리", "결과 폴더 압축", "H-OTA 체크리스트" 등을 말하거나 SWP 패치 실기 검증(swp-delivery-patch S12)의 H-OTA 부분에 들어서면 반드시 이 스킬을 사용하라. Claude Code CLI(H-OTA Studio · CVD · VN1640A 가 있는 사용자 PC, 관리자 PowerShell 권장) 전용. 라이팅은 cvd-project, CAN 출력은 can-bench-setup(Joule), H-OTA 공식 도구 명령줄 실행은 Joule joule-hota 를 부른다.
---

# hota-eval — H-OTA A·B 그룹 평가

SWP 패치 회차마다 하는 H-OTA 리프로그래밍 평가(버전 업·다운그레이드 확인)와 그 산출물을 CLI 로 처리한다. 패치 고유 재현 시험은 범위 밖이다(swp-delivery-patch S12). 사람이 하던 일 중 **판단이 필요 없는 일(이름 붙이기, 경로 넣기, 결과 읽기, 레포트·zip 만들기)을 도구가 하고, 사람은 버튼(H-OTA Start)과 확인만** 한다.

케이스 정의·경로·레포트 개체 이름은 프로젝트 프로필 `references/projects/<프로젝트>.toml` 에 있다. 첫 프로필은 `he1i_psu` 다. 다른 차종은 `_template.toml` 을 복사해 채운다.

## 도구

`python <스킬폴더>/scripts/hota_eval.py [--profile he1i_psu] [--swp 3.0.29] [--date 261008] <명령>`

| 명령 | 하는 일 | 쓰기 |
|---|---|---|
| `status` | 케이스별 .asc/.log/.png 유무·판정·이름 검사·다음 할 일 | 없음 |
| `identify --signed <폴더> [--ref <커밋>]` | aSIMS 서명본을 `aSIMS_hash_*.xml` 의 SHA-256 으로 변형 4벌에 맞춘다. 빌드 산출물(`rom_<버전>/*.s19`)과 다르면 **멈춘다** — 서명 뒤 재빌드 | 없음 |
| `bins --signed <폴더> [--ref]` | identify 뒤 서명본 .bin 을 결과 폴더로 (없으면 Hex2Binary) | 결과 폴더 |
| `prepare <케이스>[:<Rules>] [--manual]` | Report Config(.asc 경로)·OEUK 를 H-OTA 설정 파일에 넣고(백업 후) rom·target·기대를 보여 준다. 권한이 없으면 경로를 클립보드로 | H-OTA ini (관리자 터미널일 때만) |
| `collect <케이스>[:<Rules>]` | 실행 뒤 .asc/.log 확인, 캡처 png 이름 맞춤(`screenshot_dir` 설정 시), 그 자리 판정, 다시 라이팅 안내 | 결과 폴더 |
| `restore` | prepare 가 바꾼 H-OTA 설정 파일을 처음 상태로 | H-OTA ini |
| `judge [--json]` | 업·다운그레이드 판정 (소요 시간은 표시만) | 없음 |
| `names` | 이름 규칙 검사 (규칙 밖 · 없음, `.asc.asc`, `Rule`(s 빠짐) 힌트) | 없음 |
| `report --bench <joule 실행 폴더> --fbl 3.0.19 [--template] [--out] [--dry-run]` | 보드평가레포트 첨부·그림·헤더 교체 (Excel COM) 후 첨부 바이트 검증 | 결과 폴더 |
| `zip --issue <일감> --bench <폴더> [--dest]` | Redmine 첨부 묶음 (asc · log · png · bin · xlsx · CAN 벤치 · 하위 폴더별) | 지정 폴더 |
| `summary` | 결과 표 (Redmine 코멘트 · Confluence 체크리스트 7. 결과 기록에 그대로) | 없음 |

## 흐름

```
E0 준비 점검   관리자 PowerShell 에서 claude 실행(권장) · PJ_Define(버전·OEUK) · CVD · VN1640A · H-OTA 로그인(1주일마다 로그아웃)
E1 빌드        JENKINS_BUILD_TARGET ALL (커밋·push 는 지시받을 때) → swp-delivery-patch jenkins_wait.py → pull
               → Debug/OEUK_xxx/ 4벌 확인. 이 빌드 번호·커밋을 기록 (E2 --ref)
E2 서명        rom_<버전>.zip 4개를 aSIMS 에 (사람, 웹) → 받은 폴더 → identify → bins
E3 결과 폴더   04_Reprogramming/v<SWP>/<YYMMDD>/ , 이전 회차 보드평가레포트 복사
E4 A 그룹      cvd-project --version <low> --banks AB → 디버거 분리 → A1, A2 (External)
               → 다시 라이팅 → A3, A4 (BG→Repro)
E5 B 그룹      cvd-project --version <low>_test --banks AB → B1, B2(OEUK 체크) → 다시 라이팅 → B3(OEUK 해제), B4(OEUK 체크)
               케이스마다: prepare → (사람) H-OTA Start, Output log 저장, 캡처 → collect
E6 판정        judge / names — 8케이스 모두 통과, 대칭성(A2·A4 차단, B2·B4 성공)
E7 산출물      CAN 벤치(can-bench-setup) → report → zip → summary → Confluence 체크리스트 · Redmine 결과 코멘트 (미리보기 후)
```

단계별 세부·판정 기준·보드 상태 전이는 `references/flow.md`. 실기에서 겪은 함정은 `references/pitfalls.md` — **E2·E4 전에 꼭 읽는다.**

## 규칙

1. **보드에 쓰는 일은 매번 확인.** CVD 라이팅(`--yes`), H-OTA Start, joule-hota `--run` 은 실행 전마다 사용자 확인을 받는다. 한 번 승인이 다음 실행까지 가지 않는다.
2. **서명 뒤 APP 를 다시 빌드시키지 않는다.** 같은 소스라도 재빌드하면 Os 생성기가 스택 배치를 바꿔 이미지가 달라진다. identify 가 멈추면 서명한 빌드 커밋을 `--ref` 로 주고, 그 커밋의 산출물로 라이팅·PR 한다.
3. **라이팅은 항상 `--banks AB`.** A 만 쓰면 FBL 이 다른 뱅크의 옛 버전으로 부팅할 수 있다.
4. **파일 이름은 도구가 만든다.** `{대상}_PSU_{시험}(v시작_v목표)_{Rules}.asc` 6종 조합 밖의 이름은 쓰지 않는다. collect·names 가 어긋남을 알린다.
5. **H-OTA 설정 파일은 백업 후에만 바꾸고 끝나면 restore.** 파일이 `C:\ProgramData` 아래라 관리자 권한이 필요하다 — 관리자 PowerShell 에서 claude 를 실행하면 prepare 가 직접 넣는다. 일반 터미널이면 바꾸지 않고 경로를 클립보드로 넘긴다.
6. **저장소 커밋·push, Redmine·Confluence·Slack 등록은 지시받을 때만**, 미리보기 후. 결과 폴더 커밋·CURRENT 복귀·PR 은 swp-delivery-patch S13.
7. 확인한 것과 못 한 것을 나눠 보고한다. H-OTA `.asc` 는 진단 ID(0x7A3·0x7AB·0x7DF)만 기록하므로 CAN 출력 판정에 쓰지 않는다.

## 완전 CLI 모드 (파일럿 전)

H-OTA Start 까지 없애려면 Joule `joule-hota` 의 Updater `-DIRECT -task external|background|reprogram` 를 쓴다. Updater 가 Report Config·OEUK 설정을 따르는지, 결과 메시지 형식이 무엇인지 아직 실기로 확인하지 않았다. 파일럿 절차와 Joule 쪽에 필요한 개선 목록은 `references/cli-pilot.md`. 파일럿이 끝나기 전에는 반자동(위 흐름)이 기본이다.

## 참고 문서

| 파일 | 언제 |
|---|---|
| `references/flow.md` | 단계 세부, 케이스 표, 판정 기준, 보드 상태 |
| `references/pitfalls.md` | E2·E4 전 — 실기 함정과 대응 |
| `references/cli-pilot.md` | 완전 CLI 파일럿, Joule 개선 목록 |
| `references/projects/*.toml` | 프로젝트 프로필 (케이스·경로·레포트 개체) |
