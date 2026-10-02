# CVD 라이팅 · 디버깅 조작법

과제가 만들어진 뒤(init) 실제로 보드에 쓰는 절차. 차종에 상관없이 같다.
같은 `.csf` 파일을 **CLI(Claude 에게 요청)** 와 **CVD 화면(직접 버튼)** 두 가지로 쓴다.

---

## 라이팅 — CLI

```
python <스킬>\scripts\cvd_flash.py flash --name <과제명>            계획만 출력 (보드에 안 씀)
python <스킬>\scripts\cvd_flash.py flash --name <과제명> --yes      실제로 기록 → 검증
```

| 인자 | 뜻 |
|---|---|
| `--mode IMAGE` (기본) | FBL + APP |
| `--mode HSM` | HSM 만 |
| `--mode ALL` | FBL + APP + HSM |
| `--keep-data` | 데이터 영역(DTC·NvM·학습값)을 지우지 않음 |
| `--banks A` / `--banks AB` | APP 를 쓸 뱅크 (듀얼뱅크). A = 뱅크 A 만(벤더 원본) / AB = 뱅크 B 에도. 없으면 config 설정, `--yes` 로 쓰면 config 에 저장 |
| `--version <버전>` | APP·ELF 버전 폴더 (`Debug\OEUK_xxxx\<버전>\`). 없으면 config 의 버전 |
| `--rescan` | 저장소에서 FBL·HSM 을 다시 찾음 (버전 폴더가 없는 저장소는 APP·ELF 도) |

config 만 바꾸고 보드에는 쓰지 않으려면 `set --name <과제명> --version <버전>` (화면 PD 로 다른 버전을 쓸 때).
APP 뱅크 기본값만 바꾸려면 `set --name <과제명> --banks AB`.

CVD 가 스스로 실행되고 끝나면 닫힌다. 결과는 종료 코드와 `<과제명>_result.log` 로 남는다.
CVD 화면이 켜져 있으면 포트가 겹치므로 닫고 실행한다.

## 라이팅 — CVD 화면

```
1. 보드 연결 (전원 + IGN), 시작 메뉴 "CVD Projects" 로 CVD 실행   (ED/PS 가 붙은 채 켜진다)
2. 툴바 빨간 PS  ->  과제 선택
3. 툴바 빨간 PD  ->  Image / Hsm / Image&Hsm 고르고, 파일 확인 후 file load start
4. 보드 전원 재인가
```

CVD 는 스크립트로 붙인 툴바 버튼을 저장하지 않는다. 끄면 사라지고, 켤 때 실행 인수로
넘긴 스크립트가 다시 붙인다. `CVD Projects` 바로가기는 init 이 만든다
(`CVD.exe "Projects\cvd_start.csf"`, 다시 만들려면 `cvd_flash.py startup`).
기존 `CVD.exe.lnk` 처럼 `S32_Config\autostart.cmm` 을 넘기는 바로가기로 켜면 S32 쪽
ED/PS 가 뜬다 — 이름이 같으니 툴팁으로 구분한다. 그 상태에서 새 과제를 쓰려면
Program → Run Script File → `Projects\cvd_start.csf` 를 한 번 실행한다.

과제를 고르면 CPU 가 `CYT2BL-CM4` 로 잡히고 툴바에 `PD` `Ed` `PA` `VF` `RE` 가
생긴다. 버튼에는 2글자만 찍히고, 마우스를 올리면 설명(툴팁)이 뜬다.

### PD 창

기존 S32 과제의 PD 창(`loadimage.cmm`)과 같은 모양이다.

```
┌ <과제명> Program DownLoad ───────────────────────────────┐
│ Load:  (●) Image   ( ) Hsm   ( ) Image&Hsm               │
│ [ APP version 26820  (config)   change: ... set ... ]    │
│ [ ...he1i_psu_fbl_v3_0_17.sre            ] [boot_image]  │
│ [ ...\26820\he1i_psu_app_v3_0_26_Writing.s19 ] [app_image ]  │
│ [ ...HSM_Framework_..._V2_10_0.sre       ] [HSM       ]  │
│ [              file load start                        ]  │
└──────────────────────────────────────────────────────────┘
→ Erase data flash too? (DTC / NvM / learned values)   Yes / No
→ Write the APP to bank B too?   Yes = 뱅크 A·B 모두 / No = 뱅크 A 만   (Hsm 만 쓸 때는 묻지 않음)
```

- 첫 줄 `APP version 26820 (config)` 이 config 의 APP 버전이다(잠긴 칸). 경로 칸에는 그 버전 폴더의 이미지가
  채워져 있다. 다른 버전을 쓰려면 CLI `set --name <과제명> --version <버전>` 뒤 PD 를 다시
  누른다(과제를 다시 고를 필요 없음). APP 이 `_Writing.s19` 인지 확인한다.
- 옆 버튼으로 다른 파일을 고를 수 있다.
- `file load start` 뒤, 벤더 스크립트를 부르기 전에 파일이 있는지 본다. 없으면
  `File not found - nothing written (board untouched). APP=<경로>` 창만 뜨고 끝난다
  (config 의 버전 폴더가 지워졌을 때 등 → `set --version` 으로 다시 고른다).
- `Image` = FBL+APP, `Hsm` = HSM 만, `Image&Hsm` = 전부. 고르지 않은 칸은 흐리게 잠긴다.
- 기존 창의 `Erase`(전체 소거)는 없다 — SFlash 가 복구 불가(`troubleshooting.md`).
- 창에서 고른 파일은 이번 한 번만 쓰고 config 에 저장하지 않는다(결과 창에 `APP (selected file)`).
  계속 쓸 버전이면 `set --version <버전>` 으로 config 를 바꾼다(검증 지점도 같이 바뀜).

### PD 결과 창

쓰기가 끝나면 PD 가 이어서 검증(VF 와 같은 내용)을 돌리고 결과를 창으로 띄운다.

```
Flash + Verify OK - all check points match the image files          성공
Verify FAILED - flash does not match the image (first mismatch 0x…)  실패 — 다시 쓴다
Written. Verify skipped - selected FBL/APP differ from the project config   창에서 다른 파일을 고름
```

검증 지점은 config 의 FBL/APP 기준이라, 창에서 다른 파일을 골랐으면 검증을 건너뛴다.
쓰는 도중 오류가 나면 스크립트가 그 자리에서 멈추므로 **결과 창이 뜨지 않는다.**
창이 안 뜨면 메시지 창의 마지막 오류 줄을 본다.

### APP 를 쓸 뱅크 (듀얼뱅크)

CYT2BL 듀얼뱅크는 코드 플래시가 두 벌(`0x10000000` 쪽 = 지금 실행 중인 뱅크, `0x12000000` 쪽 = 다른 뱅크)이고,
FBL 이 리셋 때 어느 뱅크로 부팅할지 고른다. 버전 정보는 `0x10059000` / `0x12059000` 에 있다.

| 선택 | 뱅크 A | 뱅크 B | 언제 |
|---|---|---|---|
| **A 만** (`--banks A`, 벤더 원본) | FBL + APP | FBL 만 — APP 는 **예전 것 그대로** | 벤더 동작을 그대로 쓸 때 |
| **A·B 모두** (`--banks AB`) | FBL + APP | FBL + 같은 APP | OTA 시험 전, 두 뱅크를 같은 버전으로 맞출 때 |

A 만 쓰면 B 에 다른 버전이 남는다. FBL 이 B 로 부팅하면 그 버전이 돌아서 진단 SW 버전·OTA 결과가
기록한 버전과 달라진다(HE1i 2026-10-02: A=26810, B=26820 → H-OTA `E_NOTMATCHED_DESTINATION` 0x80004024).
검증은 다른 뱅크 지점 4곳도 읽어서 두 뱅크가 다르면 `[알림] 두 뱅크의 APP 가 다릅니다` 와 각 뱅크의 버전을 알린다.
A·B 모두는 벤더 스크립트에 주석으로 있던 B 쪽 APP 기록을 켠 것이며, 아직 실기로 기록해 본 적이 없다.

### 데이터 영역 지움 / 유지

벤더 스크립트의 원래 확인창 `Erase flash memory?` 의 Yes/No 를 CLI 에서는
`--keep-data` 로, 화면에서는 세 번째 선택창으로 고른다.

| 선택 | 지우는 범위 | 언제 |
|---|---|---|
| **지움** (기본, 원래의 Yes) | 워크 플래시 `0x14000000++0x1BFFF` (NvM/Fee) + 코드 플래시 | 보드 이력을 모를 때 |
| 유지 (원래의 No) | 명시적 소거 없이 코드만 다시 씀 | DTC·학습값을 남겨야 할 때 |

"유지"는 벤더 스크립트의 No 경로를 그대로 쓴 것이다. **새 스킬로 실기 확인한 적은
아직 없으므로** 처음 쓸 때 DTC 가 실제로 남는지 확인한다.

모드가 `ALL` 이면 HOST 와 HSM 스크립트가 연달아 돌며 둘 다 같은 선택을 따른다.
둘 다 지우면 워크 플래시 128KB 전체가 지워진다. 두 스크립트의 범위는 겹치지 않고
맞물린다.

```
코드 0x10000000~0x10027FFF   HSM  이 지움  ->  HSM 기록
코드 0x10028000~             HOST 가 지움 ->  FBL + APP (Bank A) / FBL (Bank B)
워크 0x14000000~0x1401BFFF   HOST 가 지움
워크 0x1401C000~0x1401FFFF   HSM  이 지움
```

HSM 의 erase 는 HOST 가 쓴 뒤에 돌지만 범위가 달라 FBL/APP 을 건드리지 않는다.

**지움을 고르면 DTC·학습값이 초기화된다.** 이후 진단 검증에서 "원래 없던 것"과
"이번에 지운 것"을 구분해야 한다.

### 정상 종료 로그 (CVD 메시지 창)

```
file "...TVII-B-E-2M.out" loaded.        로더
file "..._fbl_....sre" loaded.           FBL   (Bank A)
file "..._Writing.s19" loaded.           APP   (Bank A)
file "...TVII-B-E-2M.out" loaded.
file "..._fbl_....sre" loaded.           FBL   (Bank B)
Reset Target                             HOST 종료
IDCODE = 0x6BA0xxxx.
file "...HSM_Framework....sre" loaded.   HSM   1차
file "...HSM_Framework....sre" loaded.   HSM   2차 (뱅크 스왑)
Reset Target                             HSM 종료
PD: done (ALL)
```

HOST 와 HSM 을 둘 다 쓰면 `Reset Target` 이 두 번 찍힌다. 상태 표시가 `SYSDOWN`
이 되는 것은 정상이다.

> **Bank B 에는 APP 이 안 들어간다.** CVD 스크립트가 그 줄을 주석 처리해
> 두었다. T32 원본은 양쪽 다 쓴다. 부팅·점프 확인에는 지장이 없지만
> OTA 검증 전에는 확인이 필요하다.

### CLI 결과 로그 (`<과제명>_result.log`)

```
STEP=start        CVD 가 스크립트를 실행함
STEP=connected    타깃에 붙음 (아직 아무것도 쓰지 않음)
STEP=flashing     쓰는 중 — 도구는 이 단계에서 CVD 를 끄지 않는다
STEP=flashed      기록 끝
VERIFY=begin      검증 지점 읽기
RD <주소> <읽은 값> <기대값>
STEP=done
```

로그가 `start` 에서 끝났으면 연결 자체가 안 된 것이다. 전원 / IGN / 케이블 /
JTAG 클럭 순으로 본다(troubleshooting.md 의 0xEC2 항목).

---

## 검증

`VF`(화면) 또는 `verify --name <과제명>`(CLI). 보드에 쓰지 않는다.
화면의 VF 는 끝나면 `Verify OK` / `Verify FAILED` 창을 띄운다. CLI 는 창 없이
`[성공] 검증 완료` / `[실패] ...` 를 출력한다.

init 과 flash 때 도구가 FBL·APP 이미지에서 최대 16개 지점(주소와 그 값)을 골라
`config.csf` 에 적어 둔다. 검증은 그 주소를 CM4 로 읽어 이미지 값과 비교한다.
라이팅 전후 모두 쓸 수 있다 — 전에 돌리면 "지금 무엇이 올라가 있나", 후에 돌리면
"새로 써진 게 맞나".

`0xFFFFFFFF` 가 읽히면 플래시가 비어 있는 것이다. HSM 영역(`0x10000000`)은 CM4 에서
읽을 수 없어 검증하지 않는다.

---

## 디버깅

```
PA (Path Set)   연결 + 워치독 해제 + 심볼 ELF 로드 + 소스 경로, CPU 정지  ->  DEBUG
RE (Reset)      sys.down/up 후 go main                                  ->  main 에서 멈춤
```

**순서를 지켜야 한다.** `RE` 를 먼저 누르면 심볼이 없어 `go main` 이
`0x00000000` 에 브레이크포인트를 걸려다 실패한다.

`main` 에서 멈추면 강한 증거다 — 심볼 주소에 실제 코드가 있고, 리셋부터
FBL 을 거쳐 APP 스타트업까지 실행이 도달했다는 뜻이다. **디버거가 제어하는 상태이긴
하지만 FBL→APP 점프가 실제로 일어난 것이다.**

---

## 빌드가 새로 나왔을 때

과제를 다시 만들지 않는다. APP 는 버전 폴더(`Debug\OEUK_xxxx\<버전>\`)로 나오므로
flash 에 `--version <새 버전>` 을 붙인다(화면 PD 만 쓸 때는 `set --version <새 버전>`).
버전을 주지 않으면 config 의 버전(마지막으로 쓴 버전)을 쓰고, 계획에
`[알림] 현재 소스 버전은 …` 이 뜬다. 같은 버전이 다시 빌드됐으면 `[알림] … 다시 빌드됐습니다`
가 뜨고 검증 지점을 새로 계산한다(화면 PD 만 쓸 때는 `set --version <같은 버전>` 한 번).
FBL·HSM 이 바뀌었으면 `--rescan` 또는 `--fbl --hsm` 으로 직접 준다.
계획 출력에서 APP/ELF 경로의 버전 폴더가 맞는지 확인한 뒤 `--yes`.

Jenkins 가 산출물을 자동 커밋하므로 **작업 전 저장소에서 `git pull`** 을 한다.

---

## 디버거를 떼고 확인해야 하는 것

`RE` 로 `main` 에서 멈추는 것은 디버거가 리셋을 제어한 상태다. 실차 조건이
아니다. 최종 확인은 이렇게 한다.

```
1. CVD 종료, 포드 분리
2. 보드 전원 OFF -> ON
3. CAN 출력 확인
```

`go main` 후 `Go` 를 누르지 않으면 CPU 가 정지한 채라 CAN 도 안 나간다.
**CAN 이 안 나온다고 할 때 가장 먼저 의심할 것이 이것이다.**

PSU 계열은 B+ 만으로는 슬립에 머물러 CAN 을 쏘지 않는다. **IGN 도 넣어야 한다.**
CVD 포드는 타겟에 전원을 주지 않는다.

### 세 가지 상태를 구분한다

"디버거를 떼라"가 항상 맞는 것은 아니다. 아래 ③만 문제다.

```
① 미연결 (전원만)        CAN ○    실차 조건. 최종 판정
② 연결 + Go 실행 중      CAN ○    대부분의 작업이 여기서 된다
③ 연결 + 정지 (main)     CAN ✗    코드를 들여다볼 때만
```

②는 CPU 가 정상 실행 중이라 **디버거를 꽂은 채로 CANoe 로 신호를 봐도 된다.**
`RE` 로 `main` 에 멈춘 뒤 `Go` 를 누르면 된다.

| 검증 항목 | 상태 | 이유 |
|---|---|---|
| CAN 신호 확인 | ② 가능 | 실행 중이면 정상 송수신 |
| 변수 · 브레이크포인트 | ③ | 디버거를 쓰는 이유 |
| 진단 / DTC (UDS) | ② 가능 | ③에서 멈추면 P2 타임아웃으로 세션이 끊긴다 |
| 부팅 성공 최종 판정 | **①** | 리셋을 디버거가 잡고 있으면 실차와 다르다 |
| 슬립 진입 · 웨이크업 | **① 필수** | 디버거가 붙어 있으면 저전력 진입이 막히거나 달라진다 |
| 암전류 측정 | **① 필수** | 디버그 포트 자체가 전류를 끈다 |
| OTA 리프로그래밍 | **① 필수** | 뱅크 스왑과 리셋이 실제로 일어나야 한다 |

뗄 때는 전원을 내리고 포드를 분리한다.

### 워치독은 디버그 중에도 돈다

저장소 설정이 그렇게 되어 있다.

```
Configuration\Ecu\Mcal\Ecud_Wdg.arxml
   WdgDebugModeConfig = WDG_DEBUGMODE_RUN
```

**디버거를 붙이면 워치독이 멈춘다고 생각하면 안 된다.** `main` 에서 멈춰도
리셋이 안 걸리는 것은 그 시점에 아직 WdgM 이 시작되기 전이기 때문으로 보인다.
**BSW 초기화 이후 지점에 오래 멈춰 있으면 리셋될 수 있다** — 디버깅 중 갑자기
리셋되면 이것을 의심한다.

라이팅 중에 워치독과 ECC 가 꺼지는 것은 별개다. 그것은 플래시 로더가
`wdtDisable` 로 직접 끄는 것이고(`<과제명>_flash_host.csf`), 애플리케이션을
디버깅하는 상황과 다르다. `PA`(connect.csf)도 연결할 때 같은 방식으로 워치독을 끈다.
