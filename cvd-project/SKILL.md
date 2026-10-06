---
name: "cvd-project"
description: "CVD(CodeViser, JnDTech) 과제 단위로 빌드 결과(FBL/APP/HSM)를 CLI로 MCU에 기록하고 플래시 내용을 이미지와 대조 검증하는 스킬. 과제 최초 1회 init(프로젝트 폴더 조사 → 모르는 것만 질문 → 스킬 동봉 기본 틀로 생성), 이후 flash/verify. 생성된 .csf 는 CVD 화면 버튼(PD/VF/PA/RE)으로도 쓴다. 사용자가 \"CVD로 다운로드\", \"보드에 구워줘\", \"라이팅\", \"CVD init\", \"CVD 설정 만들어줘\", \"새 차종 라이팅 환경\", \"빌드 새로 나왔으니 다시 써줘\", \"보드 붙었는지 확인해줘\", \"플래시 검증해줘\", \"CVD 검증\", \"SFlash 지워도 되나\", \"Erase All 해도 되나\", \"SYSDOWN 이 뜨는데\", \"0xEC2 에러\", \"CVD 로 다운로드가 안 돼\", \"CAN 이 안 나와\", \"main 에서 멈춰\" 등을 말하면 사용한다. Claude Code CLI(CVD 가 설치된 사용자 PC) 전용. S32_Config 와 기존 loadfile.cmm 은 수정하지 않는다(읽기는 사용자 허락 시에만). T32(Lauterbach)·CANoe 설정은 범위가 아니다."
---

# cvd-project

빌드 결과(FBL/APP/HSM)를 CVD CLI로 타깃에 기록하고, 플래시 내용을 이미지 파일과 대조해 성공/실패를 종료 코드로 알려 준다. 같은 .csf 파일을 CVD 화면 버튼으로도 쓴다.

## 도구

- 실행 환경: Claude Code CLI, CVD가 설치된 Windows PC. 기본 설치 경로 `C:\JnDTech\CVI\CVD`.
- **CVD 설치를 먼저 확인한다.** `scan` 이 `[CVD]` 줄로 설치 위치를 알려 준다. `init` / `flash` / `verify` 는 `Bin\CVD.exe` 가 없으면 아무것도 만들거나 실행하지 않고 중단한다. 기본 경로에 없으면 도구가 흔한 설치 위치(C~F 드라이브 `JnDTech`, `Program Files`)를 찾아 후보를 보여 준다 — 후보를 사용자에게 확인받은 뒤 모든 명령에 `--cvd-root <설치 폴더>` 를 붙인다. 후보도 없으면 설치 경로를 묻는다.
- 도구: 이 스킬 폴더의 `scripts\cvd_flash.py`. 설치·복사하지 않고 그 자리에서 실행한다.
  `python "<이 스킬 폴더>\scripts\cvd_flash.py" <명령>`
- 라이팅 기본 틀: `assets\cyt2bl_dual\` (CYT2BL 듀얼뱅크). 원본은 CVD 의 `S32_Config\_BASE_CYT2BL_Dual` 이며 한 번 복사해 스킬에 넣은 것이다. **다른 과제 폴더(S32_Config 아래)는 참조하지 않는다.**
- 생성된 .csf 는 손으로 고치지 않는다. 경로는 도구(`flash` 인자, `set`)로 바꾼다.

### APP 버전 폴더

Jenkins(`PostPackage.bat`)는 APP 산출물을 `Debug\OEUK_xxxx\<버전>\` 에 쌓는다(`<버전>` = `PJ_Define.h` 의 `SOFTWARE_VERSION_0~4`, 예 `26820`). **파일 이름은 버전마다 같고 폴더 이름만 다르다.** 그래서:

- APP(`_Writing.s19`)와 ELF 는 **항상 고른 버전 폴더에서 한 쌍으로** 가져온다. config 에 `cfg_version` 으로 저장되고, PD 창 경로·실제 기록 파일·검증 지점·PA 심볼·결과 메시지가 모두 이 경로를 쓴다. `rom_<버전>\`(aSIMS 서명 입력)은 제외.
- **`<버전>_test\`(OEUK_TEST 빌드, H-OTA 테스트용)도 버전으로 고를 수 있고, FBL 은 APP 버전의 짝으로 자동으로 바뀐다**(cvd_flash 1.5.0).
  - `26810` → FBL `References\02_Fbl_Binary\OEUK_HE1I\*.sre`, `26810_test` → `02_Fbl_Binary\OEUK_HE1I_TEST\*.sre`. 차종 폴더는 APP 버전 폴더의 OEUK(`Debug\OEUK_HE1I\`)에서 온다.
  - init·flash·verify·set 모두 같다. 계획에 `FBL … ← APP 26810_test 의 짝 — 02_Fbl_Binary\OEUK_HE1I_TEST` 로 나오고 config 의 `cfg_fbl` 에 저장되므로 화면 PD 도 따라간다. `set --version` 으로 바꾸면 `바뀜 FBL` 이 함께 나온다.
  - test 버전인데 짝 폴더가 없으면 **아무것도 쓰지 않고 멈춘다**(일반 FBL 로 잘못 쓰지 않도록) → APP 저장소 `git pull` 또는 `--fbl`. 일반 버전인데 `02_Fbl_Binary` 가 없는 저장소는 config 의 FBL 을 그대로 쓴다.
  - `--fbl` 을 주면 짝 대신 그 파일을 쓴다.
  - "가장 새 버전"·"더 새 버전 폴더" 알림은 test 가 아닌 버전만 센다. 버전 구별 지점은 test 버전이면 같은 번호 일반 버전(26810_test ↔ 26810)과의 차이로 고른다.
- 버전 폴더가 하나면 그것을 쓴다. 여러 개면:
  - **init**: 도구가 목록만 보여 주고 멈춘다. 목록을 AskUserQuestion 으로 보여 주고 고르게 한다 — **추천(첫 옵션)은 `현재 소스` 표시된 버전**(`PJ_Define.h`), 다른 버전(예 26810)도 옵션으로 모두 보여 준다. 고른 값을 `--version` 으로 넘긴다.
  - **flash / verify**: 기본은 **config 의 버전(마지막으로 쓰거나 set 한 버전)**. 멈추지 않는다. 계획에 다른 버전과 `[알림] 현재 소스 버전은 …` 을 보여 주므로, 확인받을 때 그 알림을 반드시 짚는다. 바꾸려면 `--version`.
  - **set**: `set --name <과제명> --version <버전>` — 보드에 쓰지 않고 config 만 바꾼다(검증 지점 재계산). 화면 PD·PA 는 누를 때마다 config 를 읽으므로 과제를 다시 고를 필요 없다. 확인 없이 실행해도 된다.
- config 의 버전 폴더가 없어졌으면(정리, 로컬 `Build_all.bat` 은 옛 평면 구조로 폴더 전체를 지움) flash/set/verify 는 **아무것도 쓰지 않고 멈춘다** → 목록에서 다시 고른다.
- 같은 버전을 Jenkins 가 다시 빌드하면(경로 같고 내용만 바뀜) 도구가 `[알림] … 다시 빌드됐습니다` 를 띄우고 검증 지점을 다시 계산한다. **화면 PD 만 쓸 때는 재빌드 뒤 `set --version <같은 버전>` 한 번**을 안내한다(PD 는 옛 기준으로 검증해 잘못 FAILED 가 날 수 있다).
- **검증 지점은 다른 버전과 구별된다.** 버전 폴더가 여러 개면 16개 중 앞 4개를 다른 버전 APP 와 내용이 다른 워드로 고른다(앞쪽 차이 우선 — HE1i 는 `0x10059004` 에 SW 버전 문자열 "2681"/"2682"). 이미지 전체에서 고르게 뽑은 지점만으로는 26810/26820 이 구별되지 않아 다른 버전이 들어 있어도 OK 가 났다(2026-09-30 실기). 불일치가 이 4곳에만 나면 **보드에 다른 버전이 들어 있다는 뜻**이니, 읽은 값을 다른 버전 이미지와 비교해 어느 버전인지 알려 준다. 계산 방식이 바뀐 뒤 기존 과제는 `set --name <과제명>`(인자 없이) 한 번으로 검증 지점을 다시 계산한다.
- 버전 폴더가 없는 저장소(평면 구조)는 예전처럼 가장 최근 파일을 고르고 `--rescan` 으로 다시 찾는다.

## 폴더 구조 (도구가 만든다)

```
C:\JnDTech\CVI\CVD\Projects\
 ├── cvd_start.csf       없을 때 1회만 생성 — 툴바 ED/PS
 ├── loadfile.csf        과제 목록. init으로 과제가 추가될 때만 재생성(백업 후)
 └── <과제명>\
      <과제명>_config.csf      APP 버전·경로·검증 지점 (flash --yes / set 때 도구가 갱신)
      <과제명>_connect.csf     PA  연결+워치독 해제+심볼+소스경로
      <과제명>_flash.csf       PD  기록 (화면에서는 기존 S32 PD 와 같은 창)
      <과제명>_flash_host.csf  기본 틀 HOST .csf 변환본
      <과제명>_flash_hsm.csf   기본 틀 HSM .csf 변환본
      <과제명>_verify.csf      VF  검증 지점 읽기 → 로그
      <과제명>_reset.csf       RE  리셋 → main
      <과제명>_run.csf         CLI: 연결 → 기록 → 검증 → QUIT
      <과제명>_check.csf       CLI: 연결 → 검증 → QUIT
      <과제명>_result.log      결과 로그
      *.out                    플래시 로더

%APPDATA%\Microsoft\Windows\Start Menu\Programs\CVD Projects.lnk
                               CVD.exe "Projects\cvd_start.csf" — 켤 때 ED/PS 가 붙은 채 시작
```

## 흐름 A — init (과제당 1회)

원칙: **먼저 프로젝트 폴더에서 조사하고, 조사로 정할 수 없는 것만 사용자에게 묻는다.**

1. **프로젝트 폴더를 묻는다.** 기본값은 현재 작업 폴더. AskUserQuestion으로 "현재 폴더 `<cwd>` 사용"을 첫 옵션으로 보여 주고, 다른 경로는 직접 입력받는다.
2. `scan --repo <폴더>` 로 조사하고 결과를 표로 보여 준다: APP 버전 목록(`현재 소스` 표시) / FBL / APP(기록용 `_Writing.s19`) / ELF(심볼) / HSM / MCU / 뱅크 구성과 그 근거 / 과제명 제안 / CVD 설치 위치.
   - CVD 설치를 못 찾았으면 여기서 멈추고 설치 경로부터 확인한다(위 "도구" 참조).
   - **다른 후보가 있다고 나오면 반드시 짚는다.** 저장소에 다른 차종 파일(예: `BJ1_PSU` HSM, `SP3i_PSU_FBL`)이 섞여 있을 수 있고, 도구는 가장 최근 파일을 고른다. 경로의 차종명이 맞는지 확인받는다.
   - **FBL 은 APP 저장소 `References\02_Fbl_Binary\OEUK_<차종>\` 의 `.sre` 를 먼저 고른다**(차종 = APP 버전 폴더의 OEUK, 없으면 `PJ_Define.h` 에서 켜진 OEUK). FBL 저장소 Jenkins 결과(`Debug\OEUK_HE1I\`, `Debug\OEUK_HE1I_TEST\`)를 같은 이름 폴더로 복사해 커밋해 둔 곳이다. `OEUK_<차종>_TEST\`(H-OTA 테스트용 FBL)는 파일 이름이 같아 최근 순으로 고르면 섞이므로 scan 에서는 고르지 않고, APP `<버전>_test` 를 고를 때 짝으로 따라온다(위 "APP 버전 폴더"). 그 폴더가 없으면 예전처럼 가장 최근 파일.
   - 못 찾은 이미지는 경로를 묻는다(`--fbl --app --elf --hsm`).
   - `Debug\OEUK_*` 가 없으면 빌드 산출물이 없는 것이다. 저장소에서 `git pull` 을 안내한다(Jenkins 가 산출물을 자동 커밋한다).
3. AskUserQuestion 한 번으로 묻는다.
   - **과제명**: 제안값 기본. 영문 대문자·숫자·`_`.
   - **뱅크 구성(듀얼/싱글)**: 조사 결과를 근거와 함께 첫 옵션으로. 추론으로 넘기지 않고 반드시 답을 받는다. 틀리면 플래시가 엉뚱한 주소에 써진다.
   - **APP 버전**(버전 폴더가 여러 개일 때): `현재 소스` 버전을 첫 옵션(추천)으로, 나머지 버전도 모두 옵션으로.
   - 싱글뱅크이거나 MCU 가 CYT2BL 이 아니면 **기본 틀이 없으므로 중단하고 보고**한다.
4. `init --repo <폴더> --name <과제명> --bank <dual|single> [--version <버전>] --yes --dry-run` 으로 계획을 보여 주고 확인받는다. 계획의 `→ APP 버전 … / APP / ELF` 경로가 고른 버전 폴더인지 함께 보여 준다.
5. 확인되면 `--dry-run` 없이 실행하고 결과(변환 내역, 검증 지점 수, 시작 바로가기)를 보고한다.
   - init 은 시작 메뉴에 **`CVD Projects`** 바로가기를 만든다(있으면 다시 쓴다). CVD 는 스크립트로 붙인 툴바 버튼을 저장하지 않으므로, 켤 때 `cvd_start.csf` 를 인수로 넘겨야 ED/PS 가 뜬다. 이후 CVD 는 이 바로가기로 켜라고 안내한다.
   - 다른 CVD 바로가기(예: S32 `autostart.cmm` 을 넘기는 `CVD.exe.lnk`)는 건드리지 않고 목록만 알린다. 그쪽 버튼도 이름이 ED/PS 라 둘을 함께 띄우면 헷갈린다.
   - 이미 만든 과제에 바로가기만 필요하면 `startup`.

도구가 스스로 막는 것: 이미 있는 과제(덮어쓰지 않음), 조사 결과와 다른 뱅크 지정, MCU 계열 불일치. `--force-bank` / `--force-mcu` 는 사용자가 명시적으로 요구할 때만 쓴다.

## 흐름 B — flash (빌드마다)

```
flash --name <과제명> [--version <버전>] [--mode IMAGE|HSM|ALL] [--keep-data] [--banks A|AB] [--rescan] [--fbl ..] [--hsm ..] [--app .. --elf ..] [--yes]
set   --name <과제명> [--version <버전>] [--banks A|AB] [--rescan] [--fbl/--app/--elf/--hsm ..] [--dry-run]     (보드에 쓰지 않음)
```

`--version` 과 `--app/--elf` 는 함께 쓸 수 없다(버전을 고르면 APP·ELF 는 그 폴더에서 온다). `--app/--elf` 는 버전 폴더 밖 파일을 쓸 때만.

**쓰기 전에 반드시 사용자 확인을 받는다.** 순서:

1. `--yes` 없이 실행 → 도구가 계획과 **`[옵션]` 안내**(무엇을 쓸지 / 데이터 영역 지움·유지 / APP 를 쓸 뱅크 / APP 버전 / 이미지 경로, 지금 선택값 ▶ 와 바꾸는 인자)만 출력하고 끝난다. 보드에도 config 에도 아무것도 하지 않는다.
2. 출력된 **과제 · APP 버전 · 모드 · 데이터 영역 지움/유지 · APP 뱅크 · FBL/APP/ELF/HSM 경로**와 `[옵션]`·`[알림]` 을 그대로 보여 주고 AskUserQuestion으로 확인받는다. 사용자가 정하지 않았으면 함께 묻는다.
   - **APP 버전**: config 버전(기본). `[알림]` 에 현재 소스·더 새 버전이 나오면 그 버전도 옵션으로 보여 준다.
   - **무엇을 쓸지**: FBL+APP(IMAGE, 기본) / HSM / 전부(ALL)
   - **데이터 영역(DTC·NvM·학습값)을 지울지**: 지움(기본) / 유지(`--keep-data`). 보드 이력을 모르면 지움. 고장 기록을 남긴 채 새 빌드만 올릴 때 유지.
   - **APP 를 쓸 뱅크**(듀얼뱅크, 모드 IMAGE/ALL 이면 매번 묻는다): config 설정(`[옵션]` 의 `(config)`)을 첫 옵션으로. `뱅크 A 만`(`--banks A`, 벤더 원본 — B 에는 FBL 만 쓰고 B 의 APP 는 예전 것 그대로) / `뱅크 A·B 모두`(`--banks AB`, B 에도 같은 APP). 고른 값은 `--yes` 실행 때 config 에 저장되어 다음 기본값이 된다(화면 PD 창 첫 줄에도 보임). A 를 고르면 B 에 다른 버전이 남아 FBL 이 B 로 부팅할 때 그 버전이 돈다는 점을 짚는다 — HE1i 2026-10-02 실기: A=26810, B=26820 으로 H-OTA 가 `E_NOTMATCHED_DESTINATION`(0x80004024) 실패. `AB` 는 아직 실기로 기록해 본 적이 없다(첫 사용 시 확인 6).
3. 확인되면 같은 인자에 `--yes` 를 붙여 실행한다.

- 새 빌드가 나왔으면 작업 전 저장소 `git pull` 을 안내한다. 새 APP 버전은 `--version`(또는 `set --version`)으로, FBL·HSM 이 바뀌었으면 `--rescan` 또는 경로 직접 지정.
- CVD 화면이 켜져 있으면 포트가 겹치므로 닫고 실행하도록 안내한다.
- 검증만: `verify --name <과제명>` (보드에 쓰지 않음, 확인 없이 실행 가능) / 목록: `list`
- 설정만: `set --name <과제명> --banks A|AB` (보드에 쓰지 않음) — 화면 PD 의 기본값도 이것을 따른다.

## 결과 해석

| 종료 코드 | 뜻 | 안내 |
|---|---|---|
| 0 | 기록·검증 성공 | 필요하면 PA → RE, 최종 판정은 디버거를 떼고 전원 재투입 |
| 6 | 타깃 연결 실패 — **아무것도 쓰지 않음** | 전원·IGN·케이블. `references/troubleshooting.md` 의 0xEC2 항목 |
| 2 | 기록 미완료 | CVD 메시지 창 오류 줄 |
| 5 | 쓰기 단계 시간 초과 — **CVD 를 끄지 않았음** | CVD 화면 확인, 멈춰 있으면 사용자가 직접 닫고 다시 기록 |
| 3 | 검증 불일치 | 불일치 주소와 이미지 확인, 다시 기록. 도구가 `→ … 버전 X 와 일치` 를 내면 그 버전이 들어 있는 것 |
| 4 | 검증 미완료 | 연결 확인, `<과제명>_connect.csf` |
| 1 | 사용 오류 | 메시지대로 인자 보완 |

로그 마지막 `STEP=`(start → connected → flashing → flashed → done)로 멈춘 단계를 말한다. 도구는 **쓰는 중(flashing)에는 CVD 를 강제로 끄지 않는다.** 그 밖의 단계는 `--timeout`(기본 120초) 동안 진전이 없으면 끈다. 쓰기 한도는 `--flash-timeout`(기본 900초). HSM 영역은 CM4에서 읽을 수 없어 검증은 FBL·APP 지점으로 한다.

**두 뱅크 확인**(듀얼뱅크): 검증은 실행 중인 뱅크(`0x10…`) 지점과 함께 **다른 뱅크(`0x12…`) 지점 4곳**(버전 구별 지점을 옮긴 것)도 읽는다. APP 뱅크가 `AB` 면 다른 뱅크도 일치해야 성공, `A` 면 판정에 넣지 않고 `[알림] 두 뱅크의 APP 가 다릅니다` 와 각 뱅크가 어느 버전인지만 알린다. 이 알림이 나오면 OTA·진단의 SW 버전이 기록한 버전과 다를 수 있으니 사용자에게 꼭 전한다. `0x10…` 은 그때 실행 중인 뱅크라, FBL 이 B 로 부팅해 있으면 방금 A 에 쓴 버전과 다르게 보일 수 있다.

## CVD 화면에서 쓰기

시작 메뉴 **CVD Projects** 로 켠다(다른 바로가기로 켰으면 `Program → Run Script File → Projects\cvd_start.csf`) → **PS** → 과제 → **PD**(기록) / **Ed**(config 편집) | **PA**(연결·심볼·소스 경로) / **VF**(검증) | **RE**(리셋→main). 배치와 이름은 기존 S32 과제 툴바에 맞췄다(사용자 요청). CLI와 같은 파일을 쓴다.

화면의 **PD** 는 기존 S32 `loadimage.cmm` 과 같은 창을 띄운다: `Image` / `Hsm` / `Image&Hsm` 선택, config 의 FBL/APP/HSM 경로가 채워진 칸 3개(옆 버튼으로 다른 파일 선택 가능), `file load start` → `Erase data flash too? (DTC / NvM / learned values)` → (Image·Image&Hsm 이면) `Write the APP to bank B too?` (Yes = 뱅크 A·B 모두 / No = 뱅크 A 만). 창 첫 줄(잠긴 칸)에 config 의 APP 버전과 APP 뱅크 설정이 나온다(`APP version 26820 (config) / APP banks A (config: ...)`). 화면에서 고른 뱅크는 그 한 번만 쓰고 config 에 저장하지 않는다(기본값을 바꾸려면 CLI `set --banks`). A 만 썼는데 다른 뱅크가 다르면 결과 창이 `NOTE: bank B holds a different APP` 를 붙인다. DIALOG 정의 안(HEADER 등)에서는 CVD 가 `&매크로`를 풀지 않아 창 제목에는 넣지 않았다. 다른 버전을 쓰려면 CLI `set --version` 뒤 PD 를 다시 누른다. **벤더 스크립트를 부르기 전에 이번 모드에 필요한 파일이 있는지 보고, 없으면 `File not found - nothing written (board untouched)` 창만 띄우고 끝낸다** — 벤더 스크립트는 소거·FBL 기록 뒤에야 APP 를 읽어서, 이 확인이 없으면 보드를 지운 채 멈춘다. 기존 창의 `Erase`(전체 소거)는 넣지 않았다. 창에서 고른 파일은 그 한 번만 쓰고 config 에 저장하지 않으며, config 와 다른 FBL/APP 를 골랐으면 검증 지점이 맞지 않으므로 검증을 건너뛰고 그렇게 알린다. 쓰기가 끝나면 **자동으로 검증까지 하고 결과를 창으로 띄운다** — `Flash + Verify OK - all check points match the image files` 또는 `Verify FAILED - ... (first mismatch <주소>)`. 쓰는 도중 오류가 나면 스크립트가 멈춰 결과 창이 뜨지 않는다 — 그때는 메시지 창의 오류 줄을 본다. **VF** 도 끝나면 결과 창을 띄운다. 기존 S32_Config 과제는 그대로 계속 쓸 수 있다. 자세한 조작은 `references/usage.md`.

스킬을 갱신한 뒤 이미 만든 과제의 화면 스크립트(PD 창·툴바)만 새로 만들려면 `refresh --name <과제명>`(config·변환본 유지, loadfile.csf 는 백업 후 재생성).

## 규칙

- `S32_Config` 와 기존 `loadfile.cmm` 은 수정하지 않는다. 읽는 것도 사용자가 허락할 때만 한다 — PD 창·툴바 배치는 2026-09-30 사용자 허락으로 `loadfile.cmm`·`HE1i_PSU_Dual\loadimage.cmm` 을 읽고 맞춘 것이다.
- 이미 있는 과제는 덮어쓰지 않는다. 다시 만들려면 사용자가 폴더를 지운 뒤 init.
- **Erase All(`flash_erase_all`)은 쓰지 않고 안내하지도 않는다** — SFlash 8섹터가 복구 불가. 근거는 `references/troubleshooting.md`. 데이터 영역 초기화는 flash 의 기본 동작(데이터 영역 지움)으로 충분하다.
- 쓰기(flash `--yes`)는 매번 사용자 확인 뒤에만 실행한다.

## 조작·문제 해결 질문을 받으면

파일을 만들지 말고 참고 문서를 읽고 답한다.

- `references/usage.md` — CLI/화면 라이팅 절차, 데이터 영역 지움/유지, 정상 종료 로그, PA → RE 순서, 디버거를 떼고 확인해야 하는 것, 워치독
- `references/troubleshooting.md` — Erase All 금지, `0xEC2` 연결 실패, `SYSOFF`/`SYSDOWN`/`DEBUG` 의미, `Data.LOAD.auto` 가 심볼을 지우는 문제, 2글자 툴바 버튼

## 첫 실기 사용 시 확인

이 흐름은 아직 실기에서 끝까지 돌려 보지 않았다. 처음 쓸 때 아래를 사용자와 함께 확인하고 결과를 알린다.

1. `CVD.exe <파일>.csf` 로 CLI 실행되는지. 안 되면 결과를 사용자에게 보고하고 방법을 함께 정한다(.cmm 사본으로 우회하는 기능은 두지 않았다).
2. 로그가 `STEP=connected` 까지 가는지 — 쓰기 전 연결 확인은 `connect.csf`(SWD)로 하고 기록은 벤더 스크립트(JTAG)로 한다. 보드에 따라 한쪽만 붙을 수 있다.
3. `STEP=done` 까지 가고 검증 지점이 모두 일치하는지.
4. 데이터 영역 **유지**(`--keep-data`)로 쓴 뒤 DTC 가 실제로 남아 있는지 — 벤더 스크립트의 `No` 경로를 그대로 쓰는 것이라 실기로 확인한 적이 없다.
5. 화면 PD 창 첫 줄에 config 의 APP 버전이 나오고 경로 칸이 그 버전 폴더인지(`set --version` 으로 바꾼 뒤 PD 를 다시 눌러 따라오는지), config 의 APP 가 없을 때 `File not found - nothing written` 창만 뜨는지, Image/Hsm 선택에 따라 칸이 잠기는지, 파일 버튼(`dialog.file`)이 열리는지, `file load start` 뒤 소거 질문과 결과 창(`DIALOG.OK`)이 뜨는지, PA → RE 로 main 에 도달하는지.
6. APP 뱅크 **A·B 모두**(`--banks AB` / PD 의 뱅크 질문 Yes)로 쓴 뒤 — 로그에 `PD: APP -> bank B (map B)` 가 찍히고, 검증의 다른 뱅크 지점(`RB 0x12…`)이 모두 일치하는지, 디버거를 떼고 전원 재투입 후 진단 SW 버전과 H-OTA 결과가 기록한 버전인지. 벤더 원본에 주석으로 있던 B 쪽 APP 기록을 켠 것이라 실기로 확인한 적이 없다.

확인 기록 (HE1I_PSU, 2026-09-30, 보드 미연결):
- 확인됨: `CVD Projects` 바로가기로 켜면 ED/PS 가 붙음 → PS → PD/Ed/PA/VF/RE 툴바. PD 창 표시·경로 3칸 채움·Image/Hsm 선택에 따른 칸 잠금·파일 선택 버튼 동작. `file load start` → 소거 질문 → `PD: mode=IMAGE erase_data=YES` → `PD: HOST <FBL> / <APP>` 까지 창의 값이 그대로 넘어감.
- 보드 없이 실행하면 `flash_host.csf` 의 `initCpu` 안 `Connect`(391행)에서 `0xEC2` 로 멈춘다. 소거(`eraseFlash`)·기록(`writeFw`)보다 앞이라 아무것도 쓰지 않는다. 결과 창은 뜨지 않는 것이 정상.
- 버전 폴더(2026-09-30, 보드 미연결): PD 창 첫 줄 `APP version 26810 (config)` 와 APP 칸 `...\26810\...` 확인 → `set --version 26820` 뒤 PD 를 다시 누르자 `26820` 과 `...\26820\...` 로 따라옴(과제 재선택 없이). DIALOG 정의 안(HEADER)에서는 `&매크로`가 안 풀리고, 칸 이름 `VER` 에는 `dialog.set` 값이 안 들어갔다 → `ADD0` 칸으로 표시.
- 보드 연결(2026-09-30): PA 연결 성공(`IDCODE 0x6BA00477 → 0x6BA02477`, 26820 ELF 로드). CLI verify 가 `STEP=done` 까지 8초 — 항목 1~3 확인. 고르게 뽑은 16지점만으로는 전부 일치했지만 버전 구별 지점을 넣자 4곳 불일치 → 보드는 26810 (읽은 값이 26810 이미지와 일치). 첫 연결 실패 `Already port opened (0xF0000023)` = 다른 가상 데스크톱에 CVD 가 하나 더 떠 있었음, 이어진 `JTAG signals are something wrong ... Reset CodeViser (0xEC2)` 는 CVD 를 강제 종료한 뒤라 CodeViser USB 를 뽑았다 꽂아 해결.
- 두 뱅크(2026-10-02): 벤더 스크립트는 APP 를 뱅크 A 에만 쓰고 B 에는 FBL 만 쓴다(원본 주석 `; RTSW none at Bank B`). 26810 을 쓴 뒤 FBL 이 B(26820 남아 있음)로 부팅해 H-OTA 가 `E_NOTMATCHED_DESTINATION` 실패 — 읽어 보니 `0x10059004`="2682", `0x12059004`="2681". 그래서 APP 뱅크 선택(A / AB)과 다른 뱅크 검증을 넣었다(cvd_flash 1.4.0). 기존 과제는 `refresh --name <과제명>` 으로 flash_host 변환본·config 까지 다시 만든다.
- 실제 기록(2026-10-06, CLI): `flash --version 26810 --mode ALL --banks AB --yes` → `STEP=done` 45초, 종료 코드 0. 검증 16곳 + 다른 뱅크 `RB 0x12…` 4곳 모두 일치(`0x12059004`="2681") — 항목 6 의 기록·검증 부분 확인. 단 로그에 `PD: APP -> bank B (map B)` 줄은 없었다. FBL 은 `02_Fbl_Binary\OEUK_HE1I\he1i_psu_fbl_v3_0_18.sre`(이미지 `0x10029004` = "HE130I02", TEST 짝은 "DEV30I02"). 이어서 화면 PA → RE 로 main 도달 확인. PA 는 창을 띄우지 않으므로(심볼만 로드, CPU 정지) "아무것도 안 나온다"는 질문이 나올 수 있다 — 정상이며 RE 에서 List 창이 열린다.
- 남음(보드 필요): 4, 6 의 디버거 분리·전원 재투입 후 진단 SW 버전·H-OTA 결과, 화면 PD 의 `Flash + Verify OK (APP <버전>)` 결과 창, PD 의 `File not found` 창(config APP 가 없을 때).

## 범위 밖

- T32(Lauterbach) 설정, CANoe 설정·측정
- 싱글뱅크·CYT2BL 외 MCU (기본 틀 없음 — 필요하면 해당 기본 틀을 `assets\` 에 추가하는 작업부터)
- 벤더 스크립트의 플래시 알고리즘 수정 — 소거 확인 창을 PD 선택값으로 바꾸고, 원본에 주석으로 있던 뱅크 B APP 기록을 APP 뱅크 선택(`&cvd_banks`)으로 켜고 끄는 것 외에는 그대로 쓴다
- OTA 리프로그래밍
