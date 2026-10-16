---
name: "cvd-project"
description: "CVD(CodeViser, JnDTech) 과제 단위로 빌드 결과(FBL/APP/HSM)를 MCU에 기록하고 플래시 내용을 이미지와 대조 검증하는 스킬. 실행은 회사 저장소 Joule(D:\\Mobase\\asec_autotest_tool)의 joule-flash 를 그 자리에서 부른다(코드·라이팅 기본 틀은 저장소에 있다). 과제 최초 1회 init(프로젝트 폴더 조사 → 모르는 것만 질문 → 기본 틀로 생성), 이후 flash/verify. 생성된 .csf 는 CVD 화면 버튼(PD/VF/PA/RE)으로도 쓴다. 사용자가 \"CVD로 다운로드\", \"보드에 구워줘\", \"라이팅\", \"CVD init\", \"CVD 설정 만들어줘\", \"새 차종 라이팅 환경\", \"빌드 새로 나왔으니 다시 써줘\", \"보드 붙었는지 확인해줘\", \"플래시 검증해줘\", \"CVD 검증\", \"SFlash 지워도 되나\", \"Erase All 해도 되나\", \"SYSDOWN 이 뜨는데\", \"0xEC2 에러\", \"CVD 로 다운로드가 안 돼\", \"CAN 이 안 나와\", \"main 에서 멈춰\", \"데이터 지웠는데 값이 남아\" 등을 말하면 사용한다. Claude Code CLI(CVD 와 Joule 저장소가 있는 사용자 PC) 전용. S32_Config 와 기존 loadfile.cmm 은 수정하지 않는다(읽기는 사용자 허락 시에만). T32(Lauterbach)·CANoe 설정은 범위가 아니다."
---

# cvd-project

빌드 결과(FBL/APP/HSM)를 CVD 로 보드에 쓰고, 플래시 몇 지점을 이미지와 맞춰 본 결과를 종료 코드로 받는다.
**도구는 Joule 저장소의 `joule-flash` 다** (2026-10-16 까지 이 스킬에 있던 `cvd_flash.py` 1.5.4 를 옮김). 이 스킬은 언제·어떤 순서로 쓰고 무엇을 사람에게 확인받는지만 다룬다.

## 도구

- 저장소 `D:\Mobase\asec_autotest_tool` (Joule). 그 폴더에서 `uv run joule-flash <명령>` 으로 실행한다. 설치·복사하지 않는다.
- 사용법·옵션·종료 코드·폴더 구조·문제 해결의 정본은 저장소 **`docs/joule-flash.md`**. 조작·문제 해결 질문은 파일을 만들지 말고 그 문서를 읽고 답한다.
- 코드 `src/joule/flash/tool.py`, 라이팅 기본 틀 `src/joule/flash/assets/cyt2bl_dual/` (CYT2BL 듀얼뱅크만). 고칠 것이 생기면 저장소에서 고치고 `uv run pytest` (보드 없이 `tests/test_flash.py`).
- 저장소가 없으면 멈추고 알린다 (회사 Gitea `asec_autotest_tool` 클론 필요).
- **CVD 설치를 먼저 확인한다.** `scan` 의 `[CVD]` 줄. 기본 경로 `C:\JnDTech\CVI\CVD` 에 없으면 도구가 후보를 보이니 사용자에게 확인받고 모든 명령에 `--cvd-root <설치 폴더>`.
- 생성된 `.csf` 는 손으로 고치지 않는다. 경로는 `flash` 인자나 `set` 으로 바꾼다.
- 실행 계획대로 묻지 않고 도는 평가(`joule-run`)도 이 도구로 쓴다 - 그쪽은 계획을 만든 것이 확인이다.

## 흐름 A - init (과제당 1회)

원칙: **먼저 프로젝트 폴더에서 조사하고, 조사로 정할 수 없는 것만 묻는다.**

1. 프로젝트 폴더를 묻는다 (기본 = 현재 작업 폴더, AskUserQuestion 첫 옵션).
2. `scan --repo <폴더>` 결과를 표로 보인다: APP 버전 목록(`현재 소스` 표시) / FBL / APP / ELF / HSM / MCU / 뱅크 구성과 근거 / 과제명 제안 / CVD 위치.
   - 다른 후보가 있으면 경로의 차종 이름을 반드시 짚는다. `[주의] 같은 때 생긴 서로 다른 파일` 이면 init 은 멈추니 `--fbl/--app/--elf/--hsm` 로 고르게 한다.
   - `Debug\OEUK_*` 가 없으면 저장소 `git pull` 을 안내한다.
3. AskUserQuestion 한 번으로: **과제명**(제안값), **뱅크 구성**(조사 결과를 근거와 함께 첫 옵션 - 추론으로 넘기지 않는다), **APP 버전**(여러 개면 `현재 소스` 를 추천으로, 나머지도 옵션).
   싱글뱅크이거나 CYT2BL 이 아니면 기본 틀이 없으니 멈추고 보고한다.
4. `init --repo <폴더> --name <과제명> --bank <dual|single> [--version <버전>] --yes --dry-run` 으로 계획을 보이고 확인받은 뒤 `--dry-run` 없이.
   결과(변환 내역, 검증 지점 수, 시작 바로가기 `CVD Projects`)를 보고한다. 이후 CVD 는 그 바로가기로 켜라고 안내한다.

`--force-bank` / `--force-mcu` 는 사용자가 명시적으로 요구할 때만.

## 흐름 B - flash (빌드마다)

**쓰기 전에 반드시 사용자 확인을 받는다.**

1. `flash --name <과제명> [인자]` 를 `--yes` 없이 → 계획과 `[옵션]`·`[알림]` 만 나온다 (보드·config 그대로).
2. 과제 · APP 버전 · 모드 · APP 뱅크 · FBL/APP/ELF/HSM 경로와 `[알림]` 을 그대로 보이고 AskUserQuestion 으로 확인받는다. 정하지 않은 것은 함께 묻는다.
   - APP 버전: config 버전이 기본. `[알림]` 의 현재 소스·더 새 버전도 옵션으로.
   - 무엇을 쓸지: IMAGE(FBL+APP, 기본) / HSM / ALL. 새 보드나 다른 HSM 이면 ALL.
   - 데이터 영역(DTC·NvM·학습값)은 **언제나 지운다** - 묻지 않는다 (유지 옵션은 2026-10-16 없앰). 같은 보드에 다른 제어기를 쓰면 NvM 이 넘어오기 때문이라고 알린다.
   - APP 뱅크(듀얼뱅크, IMAGE/ALL): config 설정을 첫 옵션으로. A 를 고르면 B 에 다른 버전이 남아 FBL 이 B 로 부팅할 때 그 버전이 돈다는 점을 짚는다.
3. 확인되면 같은 인자에 `--yes`. CVD 화면은 닫아 둔다 (포트가 겹친다). 보드 B+·IGN 이 켜져 있는지 본다 - joule-deep/full 은 끝날 때 전원을 끈다.
4. 끝나면 CVD 를 닫은 상태에서 **B+·IGN1 을 함께** 껐다 켠다 (IGN1 -> B+ 끄고 3초 뒤 B+ -> IGN1, `uv run joule-relay relaybox off|on ...`).
   **B+ 만 끊으면 IGN1 이 켜진 채라 다시 부팅하지 않는다** (2026-10-16 NQ6e PSU, 데이터 영역을 실제로 지운 뒤). 포드는 꽂아 둬도 된다 (암전류만 분리).

- 검증만 `verify --name <과제명>`, 설정만 `set --name <과제명> --version/--banks ...`, 목록 `list` - 보드에 쓰지 않으니 확인 없이 실행해도 된다.
- Joule 을 갱신한 뒤(기본 틀 변환 규칙이 바뀜) 기존 과제는 `refresh --name <과제명>`.

## 결과 전하기

종료 코드와 로그 `STEP=` 로 어디서 멈췄는지 말한다 (표는 `docs/joule-flash.md`). 특히:

- 6 = 연결 실패, **아무것도 쓰지 않음** → 전원·IGN·케이블 (0xEC2 항목).
- 5 = 쓰기 단계 시간 초과, **CVD 를 끄지 않았음** → 사용자가 화면을 보고 닫는다.
- 3 에서 `-> ... 버전 X 와 일치` 가 나오면 보드에 그 버전이 들어 있다는 뜻으로 전한다.
- `[알림] 두 뱅크의 APP 가 다릅니다` 는 OTA·진단 SW 버전이 기록한 버전과 다를 수 있다는 뜻이라 꼭 전한다.

## 규칙

- `S32_Config` 와 기존 `loadfile.cmm` 은 수정하지 않는다. 읽는 것도 사용자가 허락할 때만.
- 이미 있는 과제는 덮어쓰지 않는다. 다시 만들려면 사용자가 폴더를 지운 뒤 init.
- **Erase All(`flash_erase_all`)은 쓰지 않고 안내하지도 않는다** - SFlash 8섹터 복구 불가. NvM 은 flash 가 언제나 지운다.
- **work flash 를 섹터 일부만 지우는 실험을 하지 않는다** - 2026-10-16 한 섹터만 지운 뒤 ECU 가 부팅하지 않았다 (전체를 지우고 B+·IGN1 을 함께 끊었다 켜서 복구).
- 쓰기(flash `--yes`)는 매번 사용자 확인 뒤에만.

## 범위 밖

- T32(Lauterbach), CANoe 설정·측정
- 싱글뱅크·CYT2BL 외 MCU (기본 틀부터 저장소 `src/joule/flash/assets/` 에 넣는 작업)
- 벤더 플래시 알고리즘 수정 (소거 확인 창 -> 선택값, 뱅크 B APP 기록 선택, work flash 소거 명령 `cflash.erase` 외에는 원본 그대로)
- OTA 리프로그래밍
