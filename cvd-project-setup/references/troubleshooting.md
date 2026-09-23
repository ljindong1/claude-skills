# CVD 트러블슈팅

2026-09-22 HE1i PSU 실기 작업에서 실제로 겪은 것들. 전부 조용히 실패하거나
증상이 원인을 가리키지 않는 종류라, 모르면 시간을 크게 잃는다.

---

## 생성 단계에서 자동으로 막는 것

스킬이 처리하므로 사람이 신경 쓸 필요 없다. 수동으로 만들 때만 주의.

| 함정 | 증상 | 처리 |
|---|---|---|
| `Path.cmm` 미수정 | 심볼·소스가 안 붙음. 라이팅은 되니 한참 뒤에 발견 | ELF·SourcePATH 치환 후 `verify` 로 확인 |
| `loadfile.cmm` 에 Path Set/Edit 누락 | `Path.cmm` 호출 자체가 불가 | 참조 블록을 통째로 복제해 구조 일치 |
| CRLF → LF 손상 | 파일 전체가 diff 로 뜸 | 전 과정 바이트 처리 |
| 로더가 도너 폴더 절대경로 참조 | 도너 폴더 지우면 라이팅 실패 | `.out` 동봉 + 경로 전부 재지정 |
| Debug 목록에 `_Writing.s19` | S19 엔 심볼이 없어 소스 디버깅 불가 | 라이팅 `_Writing.s19` / 심볼 `.elf` 분리 |
| cp949 한글 주석 깨짐 | 주석 파손 | 치환 대상 확장자 한정 |

---

## Erase All 은 실행하지 않는다

`cyt2blx_flash_erase_all` 은 코드/워크 플래시뿐 아니라 **SFlash 13개 섹터**를
지운다(`TARGET` 선언분). 나머지 51개는 `NOP` 이라 보호된다.

```
지움    4, 5, 6, 7, 13, 50, 51, 52, 53, 54, 55, 59, 62
복구    13, 50, 51, 52, 62(TOC2)      <- HSM 이미지가 되돌리는 것
남음    4, 5, 6, 7, 53, 54, 55, 59    <- 복구 수단 없음
        0x17000800  0x17000A00  0x17000C00  0x17000E00
        0x17006A00  0x17006C00  0x17006E00  0x17007600
```

FBL(`.sre`)·APP(`.s19`)·M0 바이너리에는 `0x17` 대역 레코드가 하나도 없다.
저장소 `References` 전체에서 SFlash 를 담은 파일은 HSM 이미지 하나뿐이고,
그것이 채우는 것이 위 5개다.

벤더 Readme(`psu_app\CryptoLib\HAE_HSM\FLASH_CMM\Readme.md`)도 HSM 스크립트에
대해 "보안 관련 설정이 포함된 sflash 영역 또한 **일부** 내용이 기록된다"
라고만 적는다. 그 "일부"가 5/13 이다.

칩 출하 시 기록되는 값으로 보이므로 보드를 못 쓰게 될 수 있다.
**NvM 을 지우고 싶으면 Program DownLoad 의 `Erase flash memory? Yes` 로 충분하다.**
그쪽은 워크 플래시와 코드 플래시만 지우고 SFlash 는 건드리지 않는다.

> 이 성질은 원본 스크립트 자체의 것이라 다른 차종·T32 에도 동일하게 해당된다.

---

## `Start debugging error by system up ! (0xEC2)` / `Error : Connect`

첫 `Connect` 가 튕기는 일이 있다. **바로 다음 줄에 `IDCODE = 0x6BA0xxxx` 가
찍히면 붙은 것**이고 그대로 진행된다. 로그 끝까지 다른 에러가 없고
`Reset Target` 이 찍혔으면 기록은 끝난 것이다.

IDCODE 도 안 찍히면 순서대로 본다.

1. 보드 전원 — CVD 포드는 타겟에 전원을 공급하지 않는다
2. 디버그 커넥터 방향·핀
3. JTAG 클럭 — `OPTION.JTAGCLOCK 10.MHz` 를 4MHz 나 1MHz 로 낮춰본다
   (같은 PC 의 `SX2_MKBD_Dual` 은 8MHz 를 쓴다)
4. 포트 타입 — `OPTION.SerialWire OFF`(JTAG) ↔ `ON`(SWD).
   PSU 는 JTAG 이 맞지만 `Path.cmm` 은 SWD 로 붙는다. 둘 다 열려 있는 보드도 있다
5. Secure Debug 잠김 — `References\03_Unlock_Secure_Debug\*.dll`

IDCODE 가 도중에 바뀌는 것은 정상이다. 라이팅 중에는 CPU 를 `CM0+` 로 잡고
(`0x6BA00477`), `Path.cmm` 이 `CM4` 로 되돌린다(`0x6BA02477`).

---

## `Data.LOAD.auto` 는 심볼 테이블을 지운다

플래시 내용을 파일과 대조하려고 아래처럼 쓰면 **심볼이 날아간다.**

```
Data.LOAD.auto "...Writing.s19" /DIFF      <-- 하지 말 것
```

`Data.LOAD` 는 기본 동작이 기존 심볼 테이블을 지우고 새로 읽는 것이다.
S19 에는 심볼이 없으니 테이블이 비고, 이후 `go main` 이
`0x00000000` 에 브레이크포인트를 걸려다 실패한다.

같은 PC 의 다른 설정들이 두 번째 파일을 올릴 때 이렇게 쓰는 이유다.

```
Data.LOAD.auto &filename1 /NosYmbol /NoRegister /NoClear
```

`/DIFF` 는 이 PC 의 CVD 설정 어디에도 사용 사례가 없다. 지원 여부가 확인되지
않았으므로 검증 목적이면 쓰지 않는 편이 낫다. **`PA` → `RE` 로 `main` 에서
멈추는 것이 더 강한 증거다** — 심볼 주소에 실제 코드가 있고 리셋부터 거기까지
실행이 도달했다는 뜻이라, 빈 플래시나 다른 빌드로는 불가능하다.

복구는 `PA` 를 다시 누르면 된다.

---

## 상태 표시가 실패처럼 보이는 것

| 표시 | 뜻 |
|---|---|
| `SYSOFF` | 디버거가 타겟에 안 붙음. 시작 전 정상 |
| `SYSDOWN` | 라이팅 스크립트가 `sys.down` 으로 끝낸 상태. **실패 아님** |
| `DEBUG` | `PA` 후 CPU 정지 상태로 붙어 있음. 디버깅 시작점 |
| `Warning : Not debug mode !` | CPU 가 실행 중이라 브레이크포인트 불가 |

`SYSDOWN` 이 정상인 이유 — 라이팅 중에는 CPU 를 `CM0+` 로 잡고 ECC 와 워치독을
꺼 둔다. 그 상태로 프로그램을 돌리면 안 되므로 다 쓴 뒤 세션을 끊고 리셋
상태로 내려놓는 것이 정상 종료다. 전원을 다시 넣으면 정상 부팅한다.

`RE`(Reset.cmm)는 `go main` 까지 하므로 **연결 확인용이 아니다.**
심볼이 없으면 실패한다. `PA` 를 먼저.

---

## 툴바에 이름이 안 보인다

`TOOLITEM "설명" "버튼표시,색" "명령"` 구조라 버튼에는 **2글자만** 찍힌다.
첫 문자열은 마우스를 올렸을 때 뜨는 툴팁이다.

| 버튼 | 색 | 뜻 |
|---|---|---|
| `PS` | 빨강 | Project Select |
| `PD` | 빨강 | Program DownLoad |
| `PA` | 빨강 | Path Set |
| `RE` | 빨강 | Reset |
| `WI` | 초록 | Window (워치) |
| `Ed` | 파랑 | 해당 스크립트 편집 |

툴바가 아예 없으면 명령창에 직접 친다.

```
CD.DO C:\JnDTech\CVI\CVD\S32_Config\loadfile.cmm
```

---

## 워치 창(`WI`)이 엉뚱한 변수를 본다

도너의 `swp_debug_watch.cmm` 을 그대로 물려받으므로 도너 프로젝트의 변수를
감시한다. 예를 들어 `RWPC_JG_Dual` 계열이면 NFC·무선충전 변수가 들어 있어
대부분 심볼 에러가 난다.

다만 AUTOSAR 공통 변수는 그대로 쓸 만하다. 실기 검증에 바로 쓰이는 것들이다.

```
EcuM_GddResetReason      Det_GaaErrors
Com_GaaRxIpduStatus      Com_GaaTxIpduStatus
ComM_GaaCurComMode       CanCM_GddBatVol
Os_GusCPULoad            GucOsError
```

필요하면 해당 제어기용으로 따로 정리해 쓴다. 스킬은 이 파일을 손대지 않는다.

---

## 도너를 잘못 고르면 플래시가 엉뚱한 곳에 써진다

가장 위험한 항목이다. **MCU 계열과 뱅크 구성이 같은 도너여야 한다.**

```
CYT2BL 듀얼뱅크   _BASE_CYT2BL_Dual (기본)  RWPC_JG_Dual  WPC_JG_Dual  WPC_NH2_Dual
CYT2B9 계열       SX2_MKBD_Dual        지우는 주소와 섹터 수가 다름
단일뱅크          WPC_Single           뱅크 전환 자체가 없음
```

설정은 멀쩡해 보이는데 결과만 틀리므로 스킬은 추론하지 않고 **반드시 확인을
받는다.** 맞는 도너가 없으면 중단한다.
