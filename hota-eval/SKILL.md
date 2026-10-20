---
name: hota-eval
description: H-OTA 리프로그래밍 평가(A 그룹 차종 빌드 다운그레이드 차단 · B 그룹 OEUK_TEST 강제 다운그레이드, 1세대 External · BG→Repro / 2세대 Wired · Wireless · Rule Units)를 H-OTA Studio 와 함께 끌고 가는 스킬. 실행은 회사 저장소 Joule(D:\Mobase\asec_autotest_tool)의 joule-hota-eval · joule-hota · joule-flash 를 그 자리에서 부른다 — 서명본 4벌 판별(aSIMS hash ↔ 빌드, 서명 뒤 재빌드 감지), bin 배치, 케이스 전 보드 준비(서명본 확인·ALL·AB 쓰기·디버거 놓기·IGN1/B+ 재투입), 케이스별 Report Config(.asc 이름)·OEUK 넣기, 실행 뒤 .log 정리·캡처 이름·자동 판정(Success · NRC 0xF4 · 27 13/14 · SW/HW 버전), 이름 규칙 검사·수정, 보드평가레포트 xlsx, Redmine 첨부 zip, 결과 표. 사용자가 "H-OTA 평가", "A 그룹 B 그룹", "리프로그래밍 평가", "업그레이드 다운그레이드 평가", "OEUK 강제 다운그레이드", "External / BG / Repro Rules", "Wired Rules", "Wireless Rules", "Rule Units", "Report Config", ".asc 파일명 알려줘", "보드평가레포트 첨부 바꿔줘", "aSIMS 서명 받았어", "서명본 bin", "26310 26320 평가", "평가 결과 정리", "결과 폴더 압축", "H-OTA 체크리스트", "hcfg 확인" 등을 말하거나 SWP 패치 실기 검증(swp-delivery-patch S12)의 H-OTA 부분에 들어서면 반드시 이 스킬을 사용하라. Claude Code CLI(H-OTA Studio · CVD · VN1640A · 릴레이 박스가 있는 사용자 PC, 관리자 PowerShell 권장) 전용.
---

# hota-eval — H-OTA A·B 그룹 평가

SWP 패치 회차마다 하는 H-OTA 리프로그래밍 평가와 그 산출물을 다룬다. **도구는 Joule 저장소다** (2026-10-20 까지 이 스킬에 있던 `hota_eval.py` 를 `joule-hota-eval` 로 옮김).
이 스킬은 언제·어떤 순서로 부르고 무엇을 사람에게 확인받는지만 다룬다. 사람은 H-OTA 의 Start 와 Output 로그 저장·캡처만 한다.

## 도구

- 저장소 `D:\Mobase\asec_autotest_tool` (Joule). 그 폴더에서 `uv run <명령>` 으로 실행한다. 설치·복사하지 않는다. 저장소가 없으면 멈추고 알린다.
- 사용법·명령·판정 기준·프로필 형식·실기 함정의 정본은 저장소 **`docs/joule-hota-eval.md`**. 조작 질문은 그 문서를 읽고 답한다.

| 명령 | 하는 일 |
|---|---|
| `uv run joule-hota-eval <결선> <명령>` | 반자동 평가 도우미 - where · status · identify · bins · flash · prepare · collect · restore · judge · names · report · zip · summary |
| `uv run joule-hota <결선> ...` | H-OTA 명령줄 (Hex2Binary · -Convert · -Rompackage · -HashValue · Updater -DIRECT) - 사람 없이 돌리는 평가 (실기 확인 전) |
| `uv run joule-flash ...` | CVD 쓰기 (`joule-hota-eval flash` 가 대신 부른다) |
| `uv run joule-full <결선> --run` | CAN 출력·동작 (레포트 TC_001, P2) |

- 케이스·버전·레포트 개체는 `configs/hota_eval/<제어기>.toml`, 빌드·결과 폴더는 제어기 `[project]`, CVD 과제·서명 결과는 제어기 `[hota]` (`cvd_project`, `signed`).
  새 제어기는 프로필을 같은 형식으로 만든다 (NQ6e = 2세대 본보기, HE1i = 1세대). 고칠 것이 생기면 저장소에서 고치고 `uv run pytest`.
- H-OTA 설정 파일을 직접 다루는 일(xml 변환, Report Config, OEUK)은 관리자 권한이 필요하다. 일반 터미널이면 UAC 로 관리자 PowerShell 을 띄워 한 번에 하거나, `prepare --manual`(클립보드)로 사람에게 넘긴다.

## 흐름

```
E0 저장 위치   joule-hota-eval <결선> where -> AskUserQuestion 으로 확인 (결과 폴더 · 레포트 · zip). 바꾸면 --result 를 끝까지
E0 준비 점검   H-OTA 로그인(1주일마다 로그아웃) · CVD 화면 닫힘 · CANoe 종료 · 릴레이 박스(joule-relay relaybox status)
E1 빌드        JENKINS_BUILD_TARGET ALL -> Debug/OEUK_<차종>/ 4벌 (swp-delivery-patch)
E2 서명        (사람) aSIMS -> 받은 zip/폴더 -> identify (멈추면 --ref <서명한 빌드 커밋>) -> bins
E3 hcfg-r      H-OTA 설정 확인: 진단 ID · partNumber(TEST 빌드는 881P1TEST0 도) · dbVersion(2세대 필수) · 블록 합 = bin 크기.
               파일을 바꾸면 H-OTA 탭을 닫고(저장 안 함) 다시 연다
E4 케이스마다  status 의 "다음" 대로:
                 flash <케이스>            계획을 보이고 확인받은 뒤 flash <케이스> --yes (보드 쓰기)
                 prepare <케이스>          출력(.asc 이름, rom, target, OEUK, 실행 방법, 기대)을 사용자에게 그대로 전한다
                 (사람) Output 창 비우기 -> Start -> Output 로그 저장 -> 캡처
                 collect <케이스> [--fix]  결과·판정을 전한다. 기대와 다르면 .log/.asc 를 읽고 원인을 찾는다
E5 판정        judge / names --fix - 대칭성 (A 다운그레이드 0xF4 차단 · B 강제 다운그레이드 성공)
E6 산출물      joule-full (CAN) -> report -> zip -> summary -> Confluence 체크리스트 · Redmine (미리보기 뒤)
```

### 2세대(CCU2)에서 기억할 것 (2026-10-20 NQ6e PSU)

- Rules 는 Wired / Wireless 둘, 케이스마다 .asc 하나. 파일 이름 Rules 자리는 `WiredRules` / `WirelessRules`.
- 다운그레이드 차단은 활성화 `31 01 FF01` -> `7F 31 F4`. 전송은 성공한다.
- OEUK 는 wired · rollback 에서만 돈다. **B4 는 Wireless 시나리오가 아니라 Rule Units**: Add Background-Transfer + Pre Procedure + Rollback + Post Procedure (Activation 해제), OEUK 체크, **아래쪽 Apply** -> Start.
- 실패한 회차 파일은 `_<까닭>NG` 를 붙여 근거로 남기고 다시 돌린다 (이름 검사가 규칙 밖으로 치지 않는다).

## 규칙

1. **보드에 쓰는 일은 매번 확인.** `flash --yes`, H-OTA Start, `joule-hota --run` 은 실행 전마다 사용자 확인을 받는다. 한 번 승인이 다음 실행까지 가지 않는다.
2. **서명 뒤 APP 를 다시 빌드시키지 않는다.** identify 가 멈추면 서명한 빌드 커밋을 `--ref` 로 주고, 그 커밋의 산출물로 쓰기·PR 한다.
3. **보드 준비는 항상 ALL·뱅크 AB·데이터 지움, 쓴 뒤 디버거 놓기 + IGN1->B+ 끄고 B+->IGN1 켜기** (`flash` 가 한다). B+ 만 끊으면 다시 부팅하지 않는다.
4. **파일 이름은 도구가 만든다.** prepare 가 넣은 이름을 그대로 쓰게 하고, collect · names 가 알리면 `--fix` 로 고친다.
5. **H-OTA 설정 파일은 백업 뒤에만 바꾸고 끝나면 `restore`.**
6. **산출물 저장 위치는 시작할 때 사용자에게 묻는다** (`where` 의 기본값을 첫 옵션으로).
7. **저장소 커밋·push, Redmine·Confluence 등록은 지시받을 때만**, 미리보기 뒤. 제품 저장소(psu_master 등)는 결과 폴더 밖은 읽기만.
8. 확인한 것과 못 한 것을 나눠 보고한다. H-OTA `.asc` 는 진단 ID 만 기록하므로 CAN 출력 판정에 쓰지 않는다.
9. 도구가 못 하는 일을 손으로 했으면 그 순서를 Joule 에 반영할 목록으로 남긴다 (나중에 CLI 로 끝까지 돌릴 수 있게).

## 범위 밖

- 패치 고유 재현 시험 (swp-delivery-patch S12), 빌드·PR (swp-delivery-patch, gitea-jenkins-setup)
- CVD 과제 만들기 (cvd-project init), CAN 평가 설정 (can-bench-setup)
