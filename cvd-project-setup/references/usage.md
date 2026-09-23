# CVD 라이팅 · 디버깅 조작법

설정이 만들어진 뒤 실제로 보드에 쓰는 절차. 차종에 상관없이 같다.

---

## 라이팅

```
1. CVD 실행, 보드 연결 (전원 + IGN)
2. 툴바 빨간 PS  ->  <차종>_<제어기>_DUAL 선택
3. 툴바 빨간 PD  ->  Image&Hsm  ->  file load start
4. "Erase flash memory?"  ->  Yes / No
5. 보드 전원 재인가
```

프로젝트를 고르면 CPU 가 `CYT2BL-CM4` 로 잡히고 툴바에 `PD` `PA` `RE` `WI` 가
생긴다. 버튼에는 2글자만 찍힌다.

### 다이얼로그

```
□ Image        FBL + APP
□ Hsm          HSM
■ Image&Hsm    셋 다            <- 이것
□ Erase        지우기만
```

처음 열면 `Image` 가 선택되어 있고 세 번째 칸(HEX)이 비활성이다. 그대로 두면
HSM 을 안 쓴다. **`Image&Hsm` 을 눌러야** 세 칸이 다 살아난다.

세 칸에 아래가 들어 있어야 한다.

```
boot_image   ...\References\02_Fbl_Binary\OEUK_xxxx\..._fbl_....sre
app_image    ...\Debug\OEUK_xxxx\..._Writing.s19        <- _Writing 확인
HEX          ...\References\01_HSM_Framework\HSM_Framework_....sre
```

### Erase 확인창

| 선택 | 지우는 범위 | 언제 |
|---|---|---|
| **Yes** | 워크 플래시 `0x14000000++0x1BFFF` (NvM/Fee) + 코드 플래시 | 보드 이력을 모를 때 |
| No | 코드만 | DTC·학습값을 남겨야 할 때 |

`Image&Hsm` 은 HOST 와 HSM 스크립트를 연달아 돌리므로 **이 창이 두 번 뜬다.**
둘 다 Yes 면 워크 플래시 128KB 전체가 지워진다. 두 스크립트의 범위가 겹치지
않고 맞물린다.

```
코드 0x10000000~0x10027FFF   HSM  이 지움  ->  HSM 기록
코드 0x10028000~             HOST 가 지움 ->  FBL + APP (Bank A) / FBL (Bank B)
워크 0x14000000~0x1401BFFF   HOST 가 지움
워크 0x1401C000~0x1401FFFF   HSM  이 지움
```

HSM 의 erase 는 HOST 가 쓴 뒤에 돌지만 범위가 달라 FBL/APP 을 건드리지 않는다.

**Yes 를 고르면 DTC·학습값이 초기화된다.** 이후 진단 검증에서 "원래 없던 것"과
"이번에 지운 것"을 구분해야 한다.

### 정상 종료 로그

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
load button C:\...                       loadimage.cmm 종료
```

`Reset Target` 이 두 번 찍히면 기록이 끝난 것이다. 상태 표시가 `SYSDOWN` 이
되는 것은 정상이다.

> **Bank B 에는 APP 이 안 들어간다.** CVD 스크립트가 그 줄을 주석 처리해
> 두었다. T32 원본은 양쪽 다 쓴다. 부팅·점프 확인에는 지장이 없지만
> OTA 검증 전에는 확인이 필요하다.

---

## 디버깅

```
PA (Path Set)   심볼 ELF 로드 + 소스 경로 지정, CPU 정지   ->  DEBUG
RE (Reset)      sys.down/up 후 go main                    ->  main 에서 멈춤
```

**순서를 지켜야 한다.** `RE` 를 먼저 누르면 심볼이 없어 `go main` 이
`0x00000000` 에 브레이크포인트를 걸려다 실패한다.

`main` 에서 멈추면 강한 증거다 — 심볼 주소에 실제 코드가 있고, 리셋부터
FBL 을 거쳐 APP 스타트업까지 실행이 도달했다는 뜻이다. **디버거 제어 하이긴
하지만 FBL→APP 점프가 실제로 일어난 것이다.**

`WI` 는 도너의 워치 변수를 그대로 쓰므로 대부분 심볼 에러가 난다.
troubleshooting.md 참조.

---

## 무인 확인 — `run --mode check`

CVD 는 `.cmm` 을 인자로 받아 실행하고 `QUIT` 으로 스스로 종료한다. 그래서
연결 상태를 GUI 없이 확인할 수 있다.

```
python scripts\cvdsetup.py run --mode check --repo "D:\...\psu_app"
```

보드에 아무것도 쓰지 않는다. 5초 안에 끝난다. 확인되는 것은 두 가지다.

  1. 타겟에 붙는가          Path.cmm 을 그대로 호출해 검증
  2. FBL 이 올라가 있는가   0x10028000 의 벡터 테이블을 읽어 판정

정상이면 이런 값이 나온다.

```
FBL_SP=0x800D000       초기 스택 포인터 — SRAM 영역
FBL_RESET=0x10028D01   리셋 벡터 — FBL 영역 + Thumb 비트
```

`0xFFFFFFFF` 면 플래시가 비어 있는 것이고, `STEP=start` 에서 끝났으면
연결 자체가 안 된 것이다. 후자는 전원 / IGN / 케이블 / JTAG 클럭 순으로 본다.

**라이팅(쓰기)은 자동화하지 않는다.** 벤더 스크립트가 지우기 직전에 사람의
확인을 받도록 되어 있고, 그 확인은 유지한다. 쓰기는 위 절차대로 사람이 한다.

## 빌드가 새로 나왔을 때

APP 파일명이 바뀌므로 목록만 갱신한다. 설정을 다시 만들 필요 없다.

```
python scripts\cvdsetup.py images --repo "D:\...\psu_app"
```

`loadimage.txt` 의 FBL/APP/HSM 과 `Path.cmm` 의 심볼 ELF 경로를 새 파일로
바꾸고 검증까지 한다.

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
`wdtDisable` 로 직접 끄는 것이고(`cyt2blx_HOST_HAE_release.csf`), 애플리케이션을
디버깅하는 상황과 다르다.
