# 프로젝트 프로필: <프로젝트>

**파일 단위는 저장소(SWP 계열) 하나**다 — 같은 저장소·같은 `PJ_Define.h` 를 쓰는 차종은 한 파일 안의 행으로, FBL·APP 은 두 열로 둔다. 새 프로젝트는 이 파일을 `<계열 또는 차종_제어기>.md` 로 복사해 채운다. 저장소에서 알아낼 수 있는 것은 조사로 채우고, 모르는 것만 사용자에게 묻는다. 확인 날짜를 남긴다.

## 기본
| 항목 | 값 |
|---|---|
| SWP 계열 | [R44] <계열명> (<MCU>, <핀>, <OTA 여부>) |
| IMS 프로젝트 | <예: CP_MOBASE_SP3i_PSU, 키 MCP0806-xxx> |
| Redmine 프로젝트 / 추적 | <프로젝트>, Task |
| 검토자 / 상태 규칙 | <해결 시 담당자, 상태 전이 순서> |
| 패치 자료 폴더 | <D:\...\v<버전>\<IMS키>\> |

## 저장소
| | FBL | APP |
|---|---|---|
| 저장소 | | |
| 로컬 경로 | | |
| 하위 프로젝트 폴더 | (없으면 "없음 — 저장소 루트가 앱 루트") | |
| 작업 브랜치 | | |
| PR 대상 / 방식 | | |
| Jenkins Job | | |

## 버전 위치
| 대상 | 파일 | 규칙 |
|---|---|---|
| APP 산출물명 | | |
| APP ECU SW 버전 | | 패치 때 유지 |
| FBL 버전 문자 | | |
| FBL 산출물명 | | |
| FBL 바이너리 (APP 저장소) | | |
| JENKINS_BUILD_TARGET | (정의 위치, 없으면 "정의 없음 → 항상 CURRENT 단일 빌드") | |
| 산출물 폴더 구조 | (`Debug/OEUK_*/<버전>/` 인지 평면인지, 활성 OEUK 변형) | |
| Doc 위치·파일명 | | |

## 구성 전제 (사전 점검 P ①)
HAE 답변의 조건이 되는 값. `precheck.md` §2-① 표의 항목을 FBL/APP 따로 채운다.

| 전제 | FBL | APP | 확인 위치 |
|---|---|---|---|
| Os 확장 등급 / MPU / Timing Protection | | | Ecud_Os |
| PFee 사용 | | | Ecud_Os PFee Task, Ecud_Mem PFEE_PART |
| UseRamCode | | | Ecud_Mem_76_Pfls MemGeneral |
| 컴파일러 (SRS 고정) | | | SCons.arxml |
| toolset / 요구 Python | | | Build.bat·site_scons, 배포본 `AutomatePatch.bat` |
| mobilgene C Studio | | | |
| MCU | | | |
| 같은 계열 차종별 양산 단계 | | | |
| 대표 차종 (HAE 참고 설정 기준) | | | |

## 당사가 수정한 HAE 파일 (교체 시 병합 대상)
| 파일 | 내용 | 근거 커밋/일감 |
|---|---|---|

## 당사 빌드 후처리
(Hook, PostPackage, UTIP, MemoryUsage 등 유지해야 할 것)

## 프로젝트 고유 판단 이력
| 규칙 | 근거 |
|---|---|
