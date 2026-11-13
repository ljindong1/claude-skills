---
name: "cvd-project"
description: "CVD(CodeViser, JnDTech) 과제 단위로 빌드 결과(FBL/APP/HSM)를 MCU에 기록하고 플래시 내용을 이미지와 대조 검증하는 스킬. 실행은 회사 저장소 Joule(D:\\Mobase\\asec_autotest_tool)의 joule-flash 를 그 자리에서 부른다(코드·라이팅 기본 틀은 저장소에 있다). 과제 최초 1회 init(프로젝트 폴더 조사 → 모르는 것만 질문 → 기본 틀로 생성), 이후 flash/compare. 생성된 .csf 는 CVD 화면 버튼(PD/VF/PA/RE)으로도 쓴다. 사용자가 \"CVD로 다운로드\", \"보드에 구워줘\", \"라이팅\", \"CVD init\", \"CVD 설정 만들어줘\", \"새 차종 라이팅 환경\", \"빌드 새로 나왔으니 다시 써줘\", \"보드 붙었는지 확인해줘\", \"플래시 검증해줘\", \"CVD 검증\", \"SFlash 지워도 되나\", \"Erase All 해도 되나\", \"SYSDOWN 이 뜨는데\", \"0xEC2 에러\", \"CVD 로 다운로드가 안 돼\", \"CAN 이 안 나와\", \"main 에서 멈춰\", \"데이터 지웠는데 값이 남아\", \"S32K3 라이팅\", \"Target power off\", \"보드가 자꾸 자요\" 등을 말하면 사용한다. Claude Code CLI(CVD 와 Joule 저장소가 있는 사용자 PC) 전용. S32_Config 와 기존 loadfile.cmm 은 수정하지 않는다(읽기는 사용자 허락 시에만). T32(Lauterbach)·CANoe 설정은 범위가 아니다."
---

# cvd-project

빌드 결과(FBL/APP/HSM)를 CVD 로 보드에 쓰고, 플래시 몇 지점을 이미지와 맞춰 본 결과를 종료 코드로 받는다.
**도구는 Joule 저장소의 `joule-flash` 다** (2026-10-16 까지 이 스킬에 있던 `cvd_flash.py` 1.5.4 를 옮김). 이 스킬은 언제·어떤 순서로 쓰고 무엇을 사람에게 확인받는지만 다룬다.

## 도구

- 저장소 `D:\Mobase\asec_autotest_tool` (Joule). 그 폴더에서 `uv run joule-flash <명령>` 으로 실행한다. 설치·복사하지 않는다.
- 사용법·옵션·종료 코드·폴더 구조·문제 해결의 정본은 저장소 **`docs/joule-flash.md`**. 조작·문제 해결 질문은 파일을 만들지 말고 그 문서를 읽고 답한다.
- 코드 `src/joule/flash/` (CLI 진입점 `cli.py`), 라이팅 기본 틀 `src/joule/flash/assets/` 두 벌 - `cyt2bl_dual`(CYT2BL·듀얼) / `s32k3_single`(S32K3·싱글). 고칠 것이 생기면 저장소에서 고치고 `uv run pytest` (보드 없이 `tests/test_flash.py`).
- 저장소가 없으면 멈추고 알린다 (회사 Gitea `asec_autotest_tool` 클론 필요).
- **CVD 설치를 먼저 확인한다.** `scan` 의 `[CVD]` 줄. 기본 경로 `C:\JnDTech\CVI\CVD` 에 없으면 도구가 후보를 보이니 사용자에게 확인받고 모든 명령에 `--cvd-root <설치 폴더>`.
- 생성된 `.csf` 는 손으로 고치지 않는다. 경로는 `flash` 인자나 `set` 으로 바꾼다.
- 실행 계획대로 묻지 않고 도는 평가(`joule-run`)도 이 도구로 쓴다 - 그쪽은 계획을 만든 것이 확인이다.

## 흐름 A - init (과제당 1회)

원칙: **먼저 프로젝트 폴더에서 조사하고, 조사로 정할 수 없는 것만 묻는다.**

1. 프로젝트 폴더를 묻는다 (기본 = 현재 작업 폴더, AskUserQuestion 첫 옵션).
2. `scan --repo <폴더>` 결과를 표로 보인다: APP 버전 목록(`현재 소스` 표시) / FBL / APP / ELF / HSM / MCU / 뱅크 구성과 근거 / 기본 틀 2벌(`▶` 가 이 저장소 MCU 의 것) / 과제명 제안 / CVD 위치.
   - 다른 후보가 있으면 경로의 차종 이름을 반드시 짚는다. `[주의] 같은 때 생긴 서로 다른 파일` 이면 init 은 멈추니 `--fbl/--app/--elf/--hsm` 로 고르게 한다.
   - `Debug\OEUK_*` 가 없으면 저장소 `git pull` 을 안내한다.
3. AskUserQuestion 한 번으로: **과제명**(제안값), **뱅크 구성**(조사 결과를 근거와 함께 첫 옵션 - 추론으로 넘기지 않는다), **APP 버전**(여러 개면 `현재 소스` 를 추천으로, 나머지도 옵션).
   CYT2BL 듀얼뱅크와 S32K3 싱글뱅크는 기본 틀이 있다. 그 밖의 조합(예: CYT2BL 싱글, CYT2B9)은 틀이 없어 도구가 멈추니 그대로 보고한다.
4. `init --repo <폴더> --name <과제명> --bank <dual|single> [--version <버전>] --yes --dry-run` 으로 계획을 보이고 확인받은 뒤 `--dry-run` 없이.
   결과(변환 내역, 검증 지점 수, 시작 바로가기 `CVD Projects`)를 보고한다. 이후 CVD 는 그 바로가기로 켜라고 안내한다.

`--force-bank` / `--force-mcu` 는 사용자가 명시적으로 요구할 때만.

## 흐름 B - flash (빌드마다)

**쓰기 전에 반드시 사용자 확인을 받는다.**

0. **전원 방식을 먼저 정한다 - 릴레이 박스가 응답하면 자동, 아니면 수동.**
   `uv run joule-power relaybox status` (릴레이를 바꾸지 않으니 확인 없이 실행). 장비 설정 `configs/devices/relaybox.toml` (R4D6F20 20채널, 포트 자동·9600·ID 1, CH1 = B+, CH2 = IGN1). **bench 마다 박스가 다르다** - TPMS 는 `relaybox_n4d8b08`(8채널·19200)이니 `joule-power relaybox_n4d8b08 status`, 쓰기도 `--power relaybox_n4d8b08`.
   - 응답하면 **자동**: 지금 B+·IGN1 공급 상태를 보인다 (IGN1 은 B+ 에 딸려 있어, `status` 의 IGN1 공급 여부는 B+ 까지 함께 본 값이다). **쓰기 전 켜기는 `flash` 가 스스로 한다** (`--power` 기본 `relaybox` - 꺼진 채널을 B+ -> IGN1 순으로 켜고 기다린 뒤 붙는다). 쓴 뒤 재투입(4번)만 릴레이 명령으로 한다.
   - 응답 없음·포트 없음이면 **수동**: 멈추지 않고 그 사실을 알린 뒤, 3·4 에서 사람에게 전원을 안내한다. 이때 **모든 `flash`·`compare` 에 `--power none` 을 붙인다** - 안 붙이면 도구가 박스를 못 열어 보드에 쓰지 않고 멈춘다. 원인(박스 12V +·GND, 포트·보율·ID, A/B bench)은 저장소 `docs/joule-power.md` "처음 붙이기" 로 짚어 준다.
1. `flash --name <과제명> [인자]` 를 `--yes` 없이 → 계획과 `[옵션]`·`[알림]` 만 나온다 (보드·config 그대로).
2. 과제 · APP 버전 · 모드 · APP 뱅크 · FBL/APP/ELF/HSM 경로와 `[알림]` 을 그대로 보이고 AskUserQuestion 으로 확인받는다. 정하지 않은 것은 함께 묻는다.
   - 전원(자동일 때): "쓰기 전 켜기는 flash 가 하고, 쓴 뒤 IGN1 -> B+ 끄고 3초 뒤 B+ -> IGN1 켜기를 릴레이로 한다" 를 함께 보인다. `flash --power` 와 `joule-power on/off` 는 묻지 않고 바로 ECU 전원을 바꾸므로 **이 확인 한 번이 전원 조작 승인**이다.
   - APP 버전: config 버전이 기본. `[알림]` 의 현재 소스·더 새 버전도 옵션으로.
   - 무엇을 쓸지: IMAGE(FBL+APP, 기본) / HSM / ALL. IMAGE 로 쓰려 하면 **도구가 보드를 먼저 읽고, 다른 제어기나 새 보드면 스스로 ALL 로 올린다** (`[모드 변경] IMAGE -> ALL` - IMAGE 는 HSM 을 안 건드려 앞 제어기 HSM 이 남기 때문이다). 사람이 미리 고를 것은 없으니 그 점을 함께 알린다. config 에 HSM 경로가 없으면 올리지 못해 멈춘다.
   - **S32K3 싱글뱅크는 틀에 HSM/HSE 가 없다** - 모드를 물을 것이 없다 (`flash_hsm.csf` 는 보드에 아무것도 쓰지 않고 안내만 한다). 그 틀에서는 **위 상향 판단을 아예 하지 않는다** (올릴 모드가 없다, 2026-11-13) - 보드를 미리 읽지도 않으니 새 보드·빈 보드에도 바로 쓴다.
   - 데이터 영역(DTC·NvM·학습값)은 **언제나 지운다** - 묻지 않는다 (유지 옵션은 2026-10-16 없앰). 같은 보드에 다른 제어기를 쓰면 NvM 이 넘어오기 때문이라고 알린다.
   - APP 뱅크(듀얼뱅크, IMAGE/ALL): config 설정을 첫 옵션으로. A 를 고르면 B 에 다른 버전이 남아 FBL 이 B 로 부팅할 때 그 버전이 돈다는 점을 짚는다.
3. 확인되면 CVD 화면은 닫아 둔다 (포트가 겹친다). 보드에 B+·IGN1 이 들어가야 한다 - joule-verify deep/full 은 끝날 때 전원을 끈다 (그대로 쓰면 종료 코드 6 / 0xEC2).
   - 자동: 같은 인자에 `--yes` 만 더해 바로 실행한다 (꺼져 있으면 도구가 켜고 기다린 뒤 붙는다 - 따로 `joule-power on` 을 돌리지 않는다).
   - 수동: "B+ -> IGN1 을 켜 주세요" 라고 안내하고, 켰다는 답을 받은 뒤 `--power none --yes`.
4. 끝나면 CVD 를 닫은 상태에서 **B+·IGN1 을 함께** 껐다 켠다. 순서 IGN1 -> B+ 끄고, 3초 뒤 B+ -> IGN1 켜고, 2초 뒤(부팅) 판정한다 (`joule-run` 과 같은 순서·시간).
   - 자동: 아래 명령을 순서대로 실행하고 끝난 뒤 `status` 로 둘 다 공급인지 보인다.
     ```
     uv run joule-power relaybox off IGN1
     uv run joule-power relaybox off B+
     (3초)
     uv run joule-power relaybox on B+
     uv run joule-power relaybox on IGN1
     ```
   - 수동: 같은 순서를 사람에게 안내한다.
   - 포드를 꽂아 둔 채 평가(부팅·슬립·암전류)를 이어 해도 된다. **`flash` 가 쓰기 뒤에 스스로 디버거를 놓는다** - 리셋 없이 붙어 디버그 전원 요청(`OPTION.DBGPWRUPREQ OFF`)을 내리고 `DisConnect` 하므로 포드를 뗀 것과 같아진다 (`joule.flash.board.cvd_session("release")`). 손으로 돌릴 CLI 는 없다 - 옛 `tools/cvd/cvd_session.py` 는 2026-10 에 없어졌다(`joule.flash.board` 로 옮김).
   - 쓰기가 실패해도(종료 코드 ≠ 0) 재투입한다. 보드에 남은 빌드로라도 부팅시켜 두기 위해서다. **5(쓰기 시간 초과)만은 예외**로, CVD 가 떠 있으니 사용자가 화면을 보고 닫았다고 답한 뒤에 재투입한다.
   **IGN1 은 B+ 뒤에서 따 온 종속 전원이다** (2026-11-03 모든 bench 를 실차와 같게 고쳤다 - `relaybox.toml` 의 IGN1 `needs = "B+"`). 그래서 B+ 를 끊으면 IGN1 도 함께 내려가 재투입이 확실하고, 거꾸로 **B+ 가 꺼진 채 IGN1 만 켜면 릴레이만 붙고 제어기에는 전원이 안 간다** - 그 명령은 도구가 멈춘다. 켜는 순서는 늘 B+ -> IGN1, 끄는 순서는 IGN1 -> B+ 다. 포드는 꽂아 둬도 된다 (암전류만 분리).

- 사람 없이 쓰기부터 평가까지 한 번에 하려면 `uv run joule-run <bench>` 를 쓴다 (저장소가 전원 켜기 -> 쓰기 -> 재투입 -> joule-verify full 을 위 순서로 한다. 박스가 응답하지 않으면 시작하지 않는다).

- 검증만 `compare --name <과제명>` (2026-11 전 이름은 `verify`), 설정만 `set --name <과제명> --version/--banks ...`, 목록 `list` - 보드에 쓰지 않으니 확인 없이 실행해도 된다.
- Joule 을 갱신한 뒤(기본 틀 변환 규칙이 바뀜) 기존 과제는 `refresh --name <과제명>`.

## 결과 전하기

종료 코드와 로그 `STEP=` 로 어디서 멈췄는지 말한다 (표는 `docs/joule-flash.md`). 특히:

- 6 = 연결 실패, **아무것도 쓰지 않음** → 전원·IGN·케이블 (0xEC2 항목).
  `Target power off (0x510200 / 0x520200)` 는 포드가 디버그 커넥터의 보드 전압(VTref)을 못 읽는다는 뜻이다. 릴레이가 '공급'이어도 날 수 있으니 디버그 케이블을 다시 꽂게 한다 (2026-10-20 NQ6e PSU, 다시 꽂고 전원 재투입 뒤 붙음).
  **커넥터를 거꾸로 꽂아도 똑같은 오류가 난다** - 2026-11-11 TPMS LT2 에서 이것 때문에 오래 헤맸다 (10핀 Cortex, 방향만 바로잡으니 바로 붙음). 스크립트를 고치기 전에 **방향부터 확인**하고, 그래도 안 되면 1번(VTref)↔3번(GND) 전압을 재게 한다 - 3.3V 가 나와야 한다. 0V 면 스크립트로 풀 수 없는 문제다.
- 5 = 쓰기 단계 시간 초과, **CVD 를 끄지 않았음** → 사용자가 화면을 보고 닫는다.
- 3 에서 `-> ... 버전 X 와 일치` 가 나오면 보드에 그 버전이 들어 있다는 뜻으로 전한다.
- `[알림] 두 뱅크의 APP 가 다릅니다` 는 OTA·진단 SW 버전이 기록한 버전과 다를 수 있다는 뜻이라 꼭 전한다.

## IGN 이 없는 제어기 (빨리 자는 보드)

전원만 넣으면 몇 초 만에 자는 제어기가 있다. 자면 디버그 전원 도메인이 내려가 `SYStem.Up` 이 `Target power off (0xEC2)` 로 실패한다 - 커넥터·전원이 멀쩡해도 그렇다.

- 깨우는 조건은 프로젝트의 `Configuration\Ecu\Ecud_EcuM.arxml` 에 있다. `EcuMWakeupSourceMask` 를 보면 그 ECU 가 무엇으로 깨는지 나온다. IGN 항목이 없으면 B+ 하나로 도는 보드이니 "IGN 을 켜라" 고 하지 않는다.
- 2026-11-11 TPMS RF 수신기(LT2): 웨이크업이 `GPT`(타이머)·`LCAN_RX`(CAN)·`RF_RX` 뿐이고 IGN 이 없다. 전원 투입 뒤 약 7초만 깨어 있었다.
- **접속을 재시도 루프로 감싸지 않는다.** `ON ERROR GOSUB` 가 오류마다 쌓여 `Script stack is overflow` 로 끝난다 (2026-11-11 확인). 슬립이 진짜 원인인지부터 가리고(커넥터 방향·VTref), 정말 필요하면 CAN 레스트버스로 깨워 둔다.

## S32K3 싱글뱅크

**`joule-flash init --bank single` 이 만든다** (2026-11-13 부터, **실기 통과** - 생성한 과제로 읽기 16지점 불일치 0, 쓰기 17초 불일치 0). 기본 틀이 MCU x 뱅크로 두 벌이다 - `cyt2bl_dual`(CYT2BL·듀얼) / `s32k3_single`(S32K3·싱글). 표(`src/joule/flash/template.py`)에 없는 조합은 도구가 멈춘다. **과제를 손으로 짜지 말고 `init` 을 쓴다.** 2026-11-11 에 손으로 만든 `TPMS_RF_RECEIVER_LT2` 가 그 생성 결과의 정답지다 (`verify`·`run`·`check` 는 바이트 동일, 나머지는 주석만 다르다). 새 MCU·뱅크 조합은 벤더 원본을 `src/joule/flash/assets/<이름>/` 에 바이트 그대로 두고 그 표와 `image.MCUS` 에 한 줄씩 더하는 일이다 (docs/joule-flash.md "기본 틀").

- **S32K3 과제를 만들 때 저장소가 사내 규정과 다르면 `--fbl/--app/--elf` 를 준다.** TPMS 저장소는 `Debug\<버전>\` 평면이고 같은 때 생긴 파일이 둘이라 `scan` 이 `[주의]` 를 찍고 init 이 멈춘다 (그것이 설계다 - 엉뚱한 차종 파일을 고르지 않는다).
- **쓰기 전에 보드를 읽지 않는다** (HSM 이 없는 MCU). 읽으면 그 접속이 남아 이어지는 쓰기가 `IF !SYStem.Up()` 을 건너뛰고, 코어가 리셋·정지하지 않은 채로 구우면 돌고 있는 APP 가 알고리즘 자리(0x20400000)를 덮어써 `Download Failed (0xF0000126)` 가 난다 - **그때 플래시는 이미 지워진 뒤다** (2026-11-13 LT2 실기에서 겪고 둘 다 고쳤다: 굽기 직전 `SYStem.Down`+`SYStem.Up`+`InitSRAM`, 그리고 그 미리 읽기를 없앰).
- **단독 `joule-flash` 는 쓰기 뒤 전원을 재투입하지 않는다** (bench 를 안 읽는다). 그대로 CAN 을 보면 ECU 가 조용하니 `joule-power <장비> cycle B+ --off-s 5` 로 넣는다. 기본 릴레이 장비가 아닌 bench 는 `--power <장비 이름>` 도 같이 준다 (TPMS 는 8채널 `relaybox_n4d8b08`).
- **데이터 영역은 언제나 지워진다** - TPMS LT2 는 NvM 부품번호가 SW 버전(F1B1)을 고르므로, 쓰고 나면 `joule-verify tpms_rf_lt2 deep --tc-file 15_IDENT --run` 으로 다시 적어야 한다 (보드 쓰기라 사용자 확인 뒤).

아래는 그 틀이 왜 그 모양인지와, 과제를 손봐야 할 때의 함정이다.

- 바탕은 벤더 `S32_Config\S32_Config_bak\JG1_MFSW\s32k3_ABSWAP_J.csf` 다 (틀 `assets\s32k3_single\` 에 바이트 그대로 들어 있다). 플래시 선언(`FLASH.Create`, `FLASH.ChangeType ... NOP`)은 **그 보드에서 쓰고 있는 T32 스크립트와 같게 두고 바꾸지 않는다** - 지우는 주소를 스스로 판단해 바꾸는 것이 가장 위험하다.
- 접속부는 프로젝트의 `References\JTAG\*.cmm` 를 베낀 것이다 (`assets\s32k3_single\connect.csf`). 그게 그 보드에서 검증된 절차다. 다른 S32K3 보드가 나오면 그 프로젝트의 `.cmm` 와 맞는지 먼저 본다.
- `_connect.csf` 는 맨 위에서 `_config.csf` 를 읽어 `&cfg_elf`·`&cfg_src` 를 쓴다 (경로를 박지 않는다 - Ed 버튼으로 고친 값이 따라가야 한다).
- **`joule-flash flash/compare/set` 의 S32K3 길은 2026-11-12 에 열렸고 2026-11-13 에 실기로 확인했다** (위). CVD 화면 버튼(PA/VF/PD/RE)과 `_run.csf`·`_check.csf` 도 그대로 쓸 수 있다. 막혀 있던 까닭은 버그가 아니라 박아 둔 상수였다 - `src/joule/flash/image.py` 의 `VERIFY_RANGE` 가 CYT2BL 주소(`0x10028000~`)라 S32K3 코드가 창 밖이어서 대조 지점이 0개가 되고, config 를 덮어쓴 뒤 종료 코드 4(대조 미완료)가 났다. 지금은 MCU 표(`image.MCUS`, 과제 config 의 `cpu` 접두어로 고른다)가 S32K3 코드 영역(`0x00400000~`)을 쓴다. 창을 넓히는 것으로는 안 됐다 - **S32K3 에서 `0x10000000` 은 데이터 플래시**이고 CYT2BL 창 안에 들어온다.
- **새 보드·빈 보드에도 그냥 쓴다 (고쳤다, 2026-11-13).** 전에는 IMAGE 로 쓸 때 도구가 보드를 먼저 읽고 "다른 제어기" 로 보면 ALL 로 올리려 했고, S32K3 과제에는 HSM 이 없어(`&cfg_hsm=""`) "`--rescan` 으로 HSM 을 찾으세요" 라며 멈췄다 - S32K3 에는 쓸 HSM 이 없으니 따라갈 수 없는 안내였다. 이제 **쓸 HSM 이 없는 틀에서는 그 판단을 하지 않는다** (`CvdProject._escalate_if_other_ecu` 가 `template().hsm is None` 이면 바로 돌아온다). 같은 날 실기에서 지워진 보드에 `flash --mode IMAGE` 가 멈춤 없이 들어갔다 (17초, 16지점 불일치 0).
- **틀이 이미 굽기 직전에 `SYStem.Down` -> `SYStem.Up` -> `GOSUB InitSRAM` 을 넣는다** - 아래 함정들은 그 까닭이다. 손으로 다시 넣거나 빼지 않는다.
  - **`set` 은 대조 지점을 다시 만든다.** 손으로 넣은 지점이 지워진다 (TPMS LT2 는 16번이 FBL 공개키 자리라 그것으로 일반/TEST 판을 가린다) - 쓰기 전에 config 를 백업하고, 끝나고 그 지점을 되돌린다.
- **무인으로 쓸 때는 `_run.csf` 가 CLI 진입점이다**: `CVD.exe "<과제폴더>\<과제>_run.csf"` 가 config -> 접속 -> 지움+쓰기 -> 대조 -> `QUIT` 까지 돌고, 진행은 `_result.log` 의 `STEP=start|connected|flashing|flashed|done` 으로 본다 (2026-11-12 TPMS LT2 에서 처음 끝까지 돌렸다 - 18초, 종료 코드 0, 16지점 일치). 실패하면 `QUIT` 에 못 가 **CVD 창이 남으므로** 다시 돌리기 전에 닫는다. `STEP=done` 이 없으면 쓰기가 끝난 것이 아니다.
- `ChangeType ... NOP` 으로 빼 둔 구간이 APP 영역 안에 있으면 **한계선을 주석으로 적어 둔다.** 코드가 커져 그 구간을 넘기면 조용히 안 써진다 (TPMS LT2: `0x004D4000~0x004FFFFF`, 2026-11-11 기준 여유 289KB).
- **굽기 직전에 `SYStem.Up` 을 넣는다.** 벤더 원본은 자기가 접속까지 하고 바로 구워서 그 줄이 없는데, PA/VF 로 **이미 붙어 있으면** 접속 블록(`IF !SYStem.Up()`)이 통째로 건너뛰어진다. 그러면 지우기는 되고 **쓰기에서 `Download Failed (0xF0000126)` + `Flash reprogram error (0x00000002)`** 가 난다 - 2026-11-11 TPMS LT2 에서 겪었다. 같은 설치의 `S32_Config_bak\s32k3_cvd.cmm` 도 굽기 직전·직후에 `SYStem.Up` 을 한다.
  - **`SYStem.Up` 한 줄로는 모자랐다.** 이미 붙어 있는 상태에서 `Up` 만 하면 코어가 리셋·정지하지 않아, 돌고 있는 APP 가 알고리즘이 올라갈 `0x20400000` 을 덮어쓴다 (2026-11-13 LT2 실기, IMAGE 미리 읽기가 남긴 접속에서). 그래서 틀은 앞에 `SYStem.Down` 을 둔다 - 붙어 있지 않을 때도 해롭지 않다.
  - **그 `SYStem.Up` 바로 뒤에 `GOSUB InitSRAM` 을 다시 넣는다.** `SYStem.Up` 이 코어를 다시 세우면 접속 블록에서 돌린 SRAM 초기화가 풀리고, `FLASH.TARGET` 이 알고리즘을 내리는 `0x20400000` 이 초기화 전이라 **같은 `Download Failed (0xF0000126)` + `Flash reprogram error (0x00000002)`** 가 난다 (2026-11-12 TPMS LT2 에서 겪음). 접속 블록 안에만 `GOSUB InitSRAM` 이 있으면 어느 길로 들어와도 굽는 순간에는 풀려 있다 - 굽기 직전이 제자리다.
  - 이때 **플래시는 이미 지워진 뒤**다. 실패했다고 보드가 그대로일 거라 말하지 말고 VF 로 확인한 뒤 전한다.
  - 플래시가 비면 ECU 소프트웨어가 없어 더 이상 자지 않는다 - 빨리 자던 보드도 이 상태에서는 접속이 편하다.
- 대조 지점은 앞 바이트가 0 인 값(예: `0x0000FFFF`)을 고르지 않는다. CVD 로그가 `FFFF` 로 찍어 사람이 불일치로 읽는다 (실제 비교는 `IF &v!=&cfg_ve<n>` 수치 비교라 통과한다).

## 규칙

- `S32_Config` 와 기존 `loadfile.cmm` 은 수정하지 않는다. 읽는 것도 사용자가 허락할 때만.
- 이미 있는 과제는 덮어쓰지 않는다. 다시 만들려면 사용자가 폴더를 지운 뒤 init.
- **Erase All(`flash_erase_all`)은 쓰지 않고 안내하지도 않는다** - SFlash 8섹터 복구 불가. NvM 은 flash 가 언제나 지운다.
- **work flash 를 섹터 일부만 지우는 실험을 하지 않는다** - 2026-10-16 한 섹터만 지운 뒤 ECU 가 부팅하지 않았다 (전체를 지우고 B+·IGN1 을 함께 끊었다 켜서 복구).
- 쓰기(flash `--yes`)는 매번 사용자 확인 뒤에만.

## 범위 밖

- T32(Lauterbach), CANoe 설정·측정
- CYT2BL·S32K3 외 MCU 의 **joule-flash 기본 틀**을 저장소 `src/joule/flash/assets/` 에 새로 넣는 작업 (joule 쪽 일이다). 있는 틀로 과제를 만드는 것은 범위 안이다 - 위 "S32K3 싱글뱅크" 참고.
- 벤더 플래시 알고리즘 수정 (소거 확인 창 -> 선택값, 뱅크 B APP 기록 선택, work flash 소거 명령 `cflash.erase` 외에는 원본 그대로)
- OTA 리프로그래밍
