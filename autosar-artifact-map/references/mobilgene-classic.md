# 모빌진 클래식 (mobilgene Classic) 실측 구조

현대오토에버 AUTOSAR Classic 플랫폼. 실제 양산 과제
(`e_sp3i_shvu_front_asr_swp_v2114`, NXP S32K312) 스캔으로 확인한 내용.

## 목차

1. 폴더 레이아웃
2. ARXML 종류
3. 계층 판정 규칙
4. 벤더 고유 모듈
5. 알려진 함정
6. 정상 범위 기준값

---

## 1. 폴더 레이아웃

```
<과제루트>/
├── Configuration/
│   ├── ECU/                        값 ARXML (BSW ECUC)         ~44 파일
│   │   ├── Mcal/                   값 ARXML (MCAL ECUC)        ~19 파일
│   │   └── ECUCD_EcucValueCollection.arxml
│   └── System/
│       ├── Bswmd/                  정의 ARXML (BSWMD)          ~50 파일
│       ├── Swcd_Bsw/               BSW 서비스 컴포넌트 (Swcd_*)
│       ├── Composition/            EcuExtract, RootComposition
│       ├── DataTypes/              AUTOSAR_DataTypes*, AUTOSAR_MemMap
│       ├── DBImport/               CAN 통신 DB (프로젝트별 이름)
│       └── Transformer/            E2E/COM 변환기
├── Generated/
│   ├── Bsw_Output/{inc,src,swcd}   BSW 생성 코드               ~360 파일
│   └── Mcal_Output/{include,src}   MCAL 생성 코드              ~275 파일
├── Static_Code/
│   ├── Modules/
│   │   ├── <모듈>/delivery/{inc,src}        벤더 정적 코드
│   │   └── b_mcal_nxp_S32K3xx/
│   │       ├── b_mcal_Base_.../header/      MCU 디바이스 헤더 (~900개, 모듈 아님)
│   │       └── b_mcal_<드라이버>_.../{include,src}
│   └── Integration_Code/           통합 코드 (MemMap 등)
├── CryptoLib/                      HSE 펌웨어 인터페이스 (외부 라이브러리)
└── References/                     문서, JTAG_LOCK 등
```

**핵심**: 정의(`Bswmd`)와 값(`ECU`)이 폴더로 분리돼 있고, BSW와 MCAL이 생성/설정 양쪽에서 갈린다.

## 2. ARXML 종류

| 종류 | 위치/패턴 | 담고 있는 태그 |
|---|---|---|
| 정의 (BSWMD) | `Configuration/System/Bswmd/Bswmd_*.arxml` | `BSW-MODULE-DESCRIPTION` |
| 값 (ECUC) | `Configuration/ECU/*.arxml` | `ECUC-MODULE-CONFIGURATION-VALUES` |
| 서비스 컴포넌트 | `Swcd_Bsw/Swcd_*.arxml`, `Bsw_Output/swcd/` | SWC 타입·포트 |
| 값 컬렉션 | `ECUCD_EcucValueCollection.arxml` | ECU 소속 값 파일 목록 |
| 통신 DB | `DBImport/*.arxml` | CAN 프레임·시그널 |
| 시스템 | `Composition/EcuExtract.arxml` 등 | 시스템·컴포지션 |

> **중요**: 정의 파일은 `ECUC-MODULE-DEF`가 아니라 **BSWMD 템플릿**을 쓴다.
> `ECUC-MODULE-DEF`만 찾으면 정의 계층이 통째로 빠진다.
> 태그로 못 찾으면 파일명(`Bswmd_CanIf` → `CanIf`) fallback이 동작한다.

## 3. 계층 판정 규칙

| 계층 | 경로 신호 |
|---|---|
| BSW | `Configuration/ECU` 직속, `Bsw_Output/`, `Static_Code/Modules/b_autosar_*` |
| MCAL | `Configuration/ECU/Mcal/`, `Mcal_Output/`, `b_mcal_*` |
| MCU 디바이스 헤더 | `b_mcal_Base_nxp_*/header/` — **모듈 아님, 집계만** |
| 외부 라이브러리 | `CryptoLib/` — **모듈 아님, 집계만** |

**값 ARXML이 `Configuration/ECU` 직속에 있으면 무조건 BSW.**
Dem·EcuM은 값 파일이 `ECU/`와 `ECU/Mcal/` 양쪽에 있어, 이 우선순위가 없으면 MCAL로 오분류된다.

## 4. 벤더 고유 모듈

표준 AUTOSAR에 없는 오토에버 확장:

| 모듈 | 추정 역할 |
|---|---|
| `CanCM` | CAN Communication Manager (배터리 모니터·채널 관리 포함) |
| `CtrlRam` | 제어기 RAM 관리 |
| `CDD_RouterIF` / `CDD_RouterTP` | PDU 라우팅 CDD (IF=신호, TP=대용량) |
| `CDD_IPC_IF` / `CDD_IPC_TP` | 프로세서 간 통신 CDD |
| `Nml` | Nm 상위 래퍼 |
| `Mdw` | 미들웨어 |
| `Opf` | (OS 관련 확장) |
| `AeWdog` | 오토에버 워치독 |
| `OsImp` / `OsProfiler` | OS 구현·프로파일러 |
| `DataLog` | 데이터 로깅 |
| `Fbl` / `Fota` | 부트로더 / OTA |
| `RamTst` / `RomTst` / `CorTst` | 메모리·코어 자가진단 |
| `HwResource` | 하드웨어 자원 기술 |

**접미사 패턴**: `_255_Autron`(트랜시버 드라이버), `_76_*`(벤더 ID 76 구현체).
AR-PACKAGE 이름 `AUTRON`이 참조 경로에 자주 등장하므로 노이즈 필터에 포함해야 한다.

## 5. 알려진 함정

1. **`AUTRON`, `ActiveEcuC`, `CommonPublishedInformation`이 모듈로 오인됨**
   → 참조 경로에서 `EcucDefs` 바로 다음 세그먼트만 취하고, 실존 모듈로 필터링

2. **컨테이너명이 의존 관계에 섞임** (`AdcChannel`, `CanController`, `DE_0001` 등)
   → 위와 동일. 필터링 없이는 의존 목록이 못 쓰게 된다

3. **`.metadata/.plugins`** — Eclipse 작업공간 잔여물. 스캔 제외

4. **`BswModuleDescription_0` 같은 템플릿 요소명** — 1글자·소문자 시작 이름과 함께 필터

5. **`Swcd_Bsw_WdgM_Fixed.arxml`** — `WdgM_Fixed`라는 가짜 모듈 생성. SWCD만 있는 파생 모듈은 상위 모듈로 병합

6. **모듈에 속하지 않는 정상 헤더** — `MemMap.h`, `modules.h`, `Soc_Ips.h`, `NmStack_Types.h`, `*_Wrapper.h`. 매칭 실패로 남겨도 무방

## 6. 정상 범위 기준값

S32K312급 바디/컴포트 제어기 기준. 크게 벗어나면 규칙을 의심한다.

| 항목 | 기준 |
|---|---|
| 모듈 수 | 130~150 (BSW ~60, MCAL ~50) |
| 미사용 모듈 | 25~30 |
| ARXML | ~195 |
| .c / .h | ~650 / ~2,230 |
| 해석 실패 ARXML | 5개 미만 |
| 매칭 실패 소스 | 15개 미만 |

**미사용 모듈 전형** (플랫폼 제공, 과제 미사용):
FlexRay 계열 7종(`Fr`, `FrIf`, `FrNm`, `FrSM`, `FrTp`, `FrArTp`, `FrTrcv`),
Ethernet 계열(`EthIf`, `EthSm`, `EthTrcv`, `SoAd`, `UdpNm`),
`Xcp`, `J1939Tp`, `StbM`, `Dbg`, `Dlt`, `Cal`, `Ea`, `Eep`, `FlsTst`, `CorTst`, `Xfrm`, `LinNm`, `Cdd`

## 7. 사례 — SHVU Front (앞좌석 시트 열선·통풍 제어기)

읽어낸 구조:

```
FlexCAN → Can → CanIf ┬→ CanTp  → CDD_RouterIF ┐
                      ├→ CanNm  → Nm           ├→ PduR → Dcm / Com → Rte
                      └→ Com                   ┘
Lpuart  → Lin → LinIf ┬→ LinSM
                      └→ LinTp  ─────────────────→ PduR
```

- 생성 코드 최다: `SchM` 102, `Rte` 92, `Wdg` 35
- 정적 코드 최다: `Os` 85, `Dcm` 54, `Dem` 45, `IoHwAb` 42
- 의존 폭 최대: `EcuM` 44개(초기화 허브), `BswM` 26개
- 보안 스택: `Csm` → `CryIf` → `Crypto`(HSE) / `Crypto_76_HaeModule`, `KeyM`
- 워치독 6중 구조: `AeWdog`, `Swt`, `Wdg`, `WdgIf`, `WdgM`, `WdgStack`, `Wdg_76_Acw` — FuSa 대응이 무겁다
- CDD 4채널(Router/IPC × IF/TP) — 프로세서 간 PDU 라우팅 존재
