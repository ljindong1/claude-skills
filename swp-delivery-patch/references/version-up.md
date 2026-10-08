# 버전업

패치마다 바꾸는 "버전"은 세 종류다. 섞어 쓰면 안 된다.

| 종류 | 의미 | 패치 때 | 예 |
|---|---|---|---|
| SWP 버전 | HAE 플랫폼 패키지 버전 | 바뀜 | APP v3.0.28 → v3.0.29, FBL v3.0.18 → v3.0.19 |
| 산출물명 | 빌드 결과 파일 이름 (SWP 버전 포함) | 바뀜 | `he1i_psu_app_v3_0_29` |
| ECU SW 버전 | 차량이 보는 제어기 SW 버전 (진단 DID, OTA 판정) | **APP 은 바꾸지 않음**, FBL 은 SWP 버전 문자 반영 | APP 26810 유지 / FBL HE130I02 → HE130J02 |

## APP

1. **산출물명** — SWP 버전을 넣는 곳(프로젝트 프로필에 정확한 목록). HE1i 예:
   - `.project` 의 `<name>` — SConstruct 가 이 값으로 산출물명을 정한다. 다른 차종 이름(sx3e_ 등)이 들어 있으면 산출물명이 틀어진다.
   - UTIP `psu_sf2.0_utip_Reprogramming.utp`, `psu_sf2.0_utip_Writing.utp` 의 LOAD/save 경로
   - aSIMS `aSIMs_sample_ini.ini` 의 FirmwareFileName
   - 이 중 Writing·aSIMs 를 빠뜨려 재빌드한 사례가 있다 → `scripts/version_bump_check.py <앱> v3_0_28 v3_0_29` 로 잔존 0 확인.
2. **ECU SW 버전**(`PJ_Define.h` 의 SOFTWARE_VERSION_0~4 등)은 패치 때 바꾸지 않는다. 평가용 상위 버전(26820)은 Jenkins ALL 빌드 스크립트가 임시로 만들고 원복한다.
3. **문서**: ReleaseNote / ModuleList / Module Change List 를 `References/Doc/...` 에 `<원래이름>_<날짜>_v<SWP>.<확장자>` 형식으로 추가(프로필 규칙).

## FBL

1. **버전 문자**: `PJ_Define.h` 의 `SOFTWARE_VERSION_5` 한 글자를 다음 문자로(예: 'I'→'J'). 결과 문자열 HE130J02 / TEST DEV30J02, 내부 버전(02)은 유지 — 프로필에 규칙 확인.
2. **산출물명**: `.project` `<name>` (`he1i_psu_fbl_v3_0_19`).
3. **확인**: 빌드된 `.sre` 의 MainSW_Version_Info 주소(HE1i: 0x10029000)를 판독해 문자열 확인.
4. **APP 저장소 반영**: 검증을 통과한 FBL 바이너리를 APP 의 `References/02_Fbl_Binary/<변형>/` 에 교체(elf/hex/map/sre, readme). FBL 검증 전에 넣지 않는다 — APP 라이팅이 이 바이너리를 짝으로 쓴다.

## 버전 문자열 잔존 확인

```
python scripts/version_bump_check.py <앱 또는 FBL 폴더> <이전 토큰> <새 토큰>
```
- git 이 추적하는 파일에서 이전 토큰이 남은 곳을 보여 준다(Debug·Generated·log 제외).
- 새 토큰이 프로필의 위치 목록에 모두 들어갔는지도 확인한다.
