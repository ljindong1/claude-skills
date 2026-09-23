---
name: cvd-project-setup
description: CVD(CodeViser, JnDTech) 디버거에 차종별 보드 라이팅 설정을 만들어 주는 스킬. AUTOSAR 저장소(psu_app) 경로 하나만 주면 차종·제어기·MCU·FBL/APP/HSM 바이너리를 자동으로 읽어내고, 검증된 템플릿(_BASE_CYT2BL_Dual)을 복제해 `<차종>_<제어기>_Dual` 설정 폴더를 만들고 loadfile.cmm 의 Project Select 에 등록한다. 사용자가 "CVD 설정 만들어줘", "코드바이저 설정", "새 차종 라이팅 설정", "보드 라이팅 환경 만들어줘", "CVD 프로젝트 추가", "디버거 설정 추가", "Project Select 에 등록해줘", "라이팅 이미지 경로 갱신", "loadimage 갱신", "빌드 새로 나왔으니 CVD 경로 바꿔줘", "CVD 설정 검증해줘", "SFlash 지워도 되나", "Erase All 해도 되나", "SYSDOWN 이 뜨는데", "0xEC2 에러", "CVD 로 다운로드가 안 돼" 등을 말하거나, 새 차종 보드를 CVD 로 라이팅할 환경이 필요하면 반드시 이 스킬을 사용하라. Claude Code CLI(사용자 PC) 전용이다 — 로컬 CVD 설치 폴더와 저장소를 직접 읽고 쓴다. 생성·등록만 하고 기존 프로젝트 폴더와 loadfile.cmm 의 기존 블록은 절대 수정·삭제하지 않는다. T32(Lauterbach) 설정, CANoe 설정, 실기 검증 수행은 범위가 아니다.
---

# cvd-project-setup

CVD(CodeViser) 에 차종별 보드 라이팅 설정을 만든다.

CVD 설정은 빈 폴더에서 새로 만들 수 없다. 플래시 지우는 주소, 뱅크 전환
레지스터, 로더 올리는 방식이 전부 `.csf` 스크립트에 박혀 있다. **기존 설정을
복제해 경로와 이름만 바꾸는 것**이 유일한 방법이고, 이 스킬은 그 복제 과정에서
조용히 실패하는 지점들을 막는다.

2026-09-22 HE1i PSU 실기 작업을 근거로 만들었다. 그때 밟은 함정이 전부
`references/troubleshooting.md` 에 있다.

## 절대 규칙

- **도너·템플릿 폴더는 읽기만 한다.** 수정·삭제하지 않는다.
- **`loadfile.cmm` 은 공용 파일이다.** 타임스탬프 백업 후 **블록 추가만** 한다.
  기존 블록은 건드리지 않는다.
- 대상 폴더나 등록명이 **이미 있으면 중단하고 보고**한다. 덮어쓰지 않는다.
- **도너는 사용자 확인을 받는다.** MCU 계열·뱅크 구성이 다른 도너를 쓰면
  플래시가 엉뚱한 주소에 써진다. 추론으로 넘기지 않는다.
- `create` 는 `verify` 통과를 확인한 뒤에만 완료로 보고한다.
- 저장소(`psu_app`)는 **읽기만** 한다.

## 도구

`scripts/cvdsetup.py` 가 결정적으로 처리한다. Claude 는 입력 확인과 결과 해석만
한다. 파일을 직접 편집하지 말고 스크립트를 쓴다.

```
survey                          설치·도너 후보·등록 현황
plan   --repo <psu_app>         저장소 인식 결과 + 변경 예정 (파일 변경 없음)
create --repo <psu_app> --yes   생성 + 등록 + 검증
verify --name <프로젝트> [--donor <도너>]
images --repo <psu_app>         loadimage.txt / Path.cmm ELF 경로만 갱신
```

옵션: `--name` 폴더명 지정, `--donor` 도너 지정, `--bank dual|single`.

`CVD_S32_CONFIG` 환경변수로 대상 폴더를 바꿀 수 있다. **시험용이다.**
실제 작업에서는 쓰지 않는다.

## 실행 위치

Claude Code CLI(사용자 PC). 기본 경로는 아래이며 `survey` 로 확인한다.

```
C:\JnDTech\CVI\CVD\S32_Config     설정 루트
C:\JnDTech\CVI\CVD\Bin\CVD.exe    실행 파일
```

## 전체 흐름

```
survey   →   plan   →   [사용자 확인]   →   create   →   보고
                             │
                    차종 / MCU / 뱅크 / 도너
```

## 0. 사전 점검

`survey` 를 돌려 CVD 설치와 도너 후보를 확인한다. `_BASE_CYT2BL_Dual` 이 없으면
**만들지 먼저 묻는다** — 검증된 CYT2BL 듀얼뱅크 설정에서 폴더명을 치환하고
프로젝트 고유값을 토큰으로 바꾼 것이다.

Project Select 격자에 빈 자리가 없으면 중단하고 보고한다.

## 1. 저장소 인식

`plan --repo <psu_app>` 이 아래를 자동으로 읽는다. 사용자에게 표로 보여준다.

| 항목 | 출처 |
|---|---|
| 차종 · 제어기 | `References\01_HSM_Framework\*.sre` 의 `rel_<차종>_<제어기>_V` |
| 사양 폴더 | `Debug\OEUK_*` |
| APP 라이팅 | `Debug\OEUK_*\*_Writing.s19` |
| APP 심볼 | `Debug\OEUK_*\*.elf` |
| FBL | `References\02_Fbl_Binary\OEUK_*\*.sre` |
| HSM | `References\01_HSM_Framework\*.sre` |
| MCU | `Configuration` 의 arxml |

**차종 표기는 HSM 파일명을 기준으로 삼는다.** 폴더는 `OEUK_HE1I`(대문자),
`.project` 는 `he1i`(소문자)라 서로 다르다. HSM 의 `rel_HE1i_PSU` 가 정식이다.

`Debug\OEUK_*` 가 없으면 빌드 산출물이 없는 것이다. `git pull` 을 안내한다.

## 2. 사용자 확인 (1회)

`plan` 결과를 보여주고 아래를 확인받는다. **확인 없이 `create` 하지 않는다.**

- 차종 · 제어기 · 프로젝트 폴더명
- MCU 와 **뱅크 구성(듀얼/단일)** — 자동 추론하지 않는다. 틀리면 위험하다
- 도너 — CYT2BL 듀얼뱅크면 `_BASE_CYT2BL_Dual` 이 기본. 다른 계열이면 해당
  도너를 제시하고, 맞는 것이 없으면 중단한다
- 대상 폴더가 이미 있으면 그 사실

## 3. 생성

`create --repo <psu_app> --yes`. 스크립트가 순서대로 한다.

1. 도너 복제
2. 폴더명 치환 (`.cmm` / `.csf` / `.txt`, 바이트 단위라 CRLF 보존)
3. `&FLASH_LOADER` 경로를 **전부 대상 폴더 기준 절대경로로 재지정**
   — 상대 파일명과 도너 루트가 남지 않게 한다
4. 토큰 5종 채움 — 심볼 ELF, 소스 경로, FBL, APP, HSM
5. `loadfile.cmm` 에 블록 추가 — 참조 블록을 통째로 복제하므로
   `Path Set` / `Path Edit` 툴버튼이 빠지지 않는다. 빈 격자 슬롯을 계산해 배치
6. `읽어보세요.txt` 생성 (`assets/readme_template.txt` 기반)

## 4. 검증

`create` 가 끝나면 `verify` 가 자동으로 돈다. 6가지를 본다.

```
도너명 잔여 참조        0건이어야 함
치환 토큰 잔여          없어야 함
이미지 3종 존재         FBL / APP(_Writing.s19) / HSM
Path.cmm 심볼 ELF       .elf 이고 실재해야 함
플래시 로더             .out 동봉 + 외부 폴더 참조 0건
loadfile.cmm 등록       정확히 1건
```

하나라도 걸리면 **완료로 보고하지 않는다.** 무엇이 왜 걸렸는지 설명한다.

## 5. 보고

```
## CVD 설정 생성 결과

| 항목 | 값 |
| 프로젝트 | HE1i_PSU_Dual  (Project Select 에 HE1I_PSU_DUAL) |
| 폴더 | C:\JnDTech\CVI\CVD\S32_Config\HE1i_PSU_Dual |
| 도너 | _BASE_CYT2BL_Dual |
| 차종 / MCU | HE1i / PSU / CYT2BL7CAS |
| 이미지 | FBL … / APP … / HSM … |
| loadfile.cmm | 블록 추가, 백업 loadfile.cmm.bak_<날짜> |
| 검증 | 전체 통과 |

사용법은 폴더의 읽어보세요.txt 참조.
```

## 6. 첫 라이팅 안내

생성만 해 놓고 "읽어보세요.txt 참조"로 끝내지 않는다. **처음 쓰는 사람은
버튼 위치부터 막힌다.** 아래를 한 단계씩 안내하고 **각 단계에서 사용자 응답을
기다린다.** 전부 한꺼번에 쏟아내지 않는다.

**0) 보드 준비** — 전원과 IGN 을 넣었는지 확인한다. PSU 계열은 B+ 만으로는
슬립에 머물러 CAN 을 쏘지 않는다. CVD 포드는 타겟에 전원을 주지 않는다.

**1) 프로젝트 선택** — 툴바의 **빨간 `PS`**. 버튼에는 2글자만 찍히고
"Project Select" 는 마우스를 올렸을 때 뜨는 툴팁이다. 툴바가 안 보이면
명령창에 `CD.DO C:\JnDTech\CVI\CVD\S32_Config\loadfile.cmm`.

고른 뒤 툴바에 `PD` `PA` `RE` `WI` 가 생겼는지 확인받는다. 안 생기면
등록 블록 문제이므로 `verify` 를 돌린다.

**2) 다운로드** — **빨간 `PD`** → 창이 뜨면 **`Image&Hsm` 을 눌러야 한다.**
처음 열면 `Image` 가 선택돼 있고 세 번째 칸(HEX)이 비활성이라 그대로 두면
HSM 을 안 쓴다. 세 칸의 경로가 맞는지, 특히 **APP 이 `_Writing.s19`** 인지
확인받는다.

**3) Erase 확인창** — **두 번 뜬다.** HOST 와 HSM 스크립트가 각각 묻는다.
보드 이력을 모르면 둘 다 `Yes`. 그러면 워크 플래시 128KB 전체가 지워져
NvM/Fee 가 초기화되고, DTC·학습값도 같이 날아간다는 것을 알린다.

**4) 결과 확인** — 로그에 **`Reset Target` 이 두 번** 찍혔는지 본다.
상태가 `SYSDOWN` 이 되는 것은 **정상 종료**다. 실패로 오해하지 않게 짚어준다.

**5) 동작 확인** — `PA` → `RE` 순서로 누르면 `main` 에서 멈춘다.
순서를 바꾸면 심볼이 없어 실패한다.

**6) 최종 판정** — **디버거를 떼고 전원만으로 뜨는지**가 진짜 확인이다.
`RE` 는 디버거가 리셋을 제어한 상태이고, `main` 에서 멈춘 채 `Go` 를 안 누르면
CPU 가 정지해 있어 CAN 도 안 나간다. CAN 이 안 나온다는 문의의 첫 번째
의심 대상이 이것이다.

막히면 `references/troubleshooting.md` 를 읽고 원인을 좁힌다. 사용자가
"익숙하다"고 하면 0~6 을 건너뛰고 요약만 준다.

## 빌드가 새로 나왔을 때

설정을 다시 만들지 않는다. `images --repo <psu_app>` 으로 `loadimage.txt` 와
`Path.cmm` 의 ELF 경로만 갱신하고 검증한다.

작업 전 저장소에서 `git pull` 을 안내한다 — Jenkins 가 산출물을 자동 커밋한다.

## 조작·문제 해결 질문을 받으면

파일을 만들지 말고 참고 문서를 읽고 답한다.

- `references/usage.md` — 라이팅·디버깅 절차, Erase 확인창, 정상 종료 로그,
  `PA` → `RE` 순서, 디버거를 떼고 확인해야 하는 것
- `references/troubleshooting.md` — **Erase All 금지(SFlash 복구 불가 8섹터)**,
  `0xEC2` Connect 실패, `SYSOFF`/`SYSDOWN`/`DEBUG` 의미,
  `Data.LOAD.auto` 가 심볼을 지우는 문제, 2글자 툴바 버튼, 도너 선택 위험

특히 **`Erase All` 은 실행하지 말라고 답한다.** SFlash 13섹터를 지우는데
HSM 이미지가 되돌리는 것은 5개뿐이고, 나머지 8개는 저장소 어느 이미지에도 없다.
NvM 초기화는 Program DownLoad 의 `Erase flash memory? Yes` 로 충분하다.

## 범위 밖

- T32(Lauterbach) 설정 — 구조는 같지만 이 스킬은 다루지 않는다
- CANoe 설정·측정 — 별도
- 실기 검증 수행·판정, OTA 리프로그래밍
- 도너 스크립트의 플래시 알고리즘 수정 — 벤더 배포본을 그대로 쓴다
- 기존 프로젝트 폴더·`loadfile.cmm` 기존 블록의 수정·삭제
