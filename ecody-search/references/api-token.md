# eCoDY 개인 액세스 토큰(PAT) 발급·등록 — IMS · ECM

두 사이트 모두 **토큰 방식이 기본**이다(크롬·OTP 세션 불필요). 토큰이 없거나 만료되면 그 사이트만 크롬 방식으로 폴백한다.

| 사이트 | 환경변수 | 확인 명령 | 확인 엔드포인트 |
| --- | --- | --- | --- |
| eCoDY-IMS (Jira DC 10.3) | `ECODY_IMS_TOKEN` | `python scripts\ims_api.py check` | `/rest/api/2/myself` |
| eCoDY-ECM (Confluence DC 9.2) | `ECODY_ECM_TOKEN` | `python scripts\ecm_api.py check` | `/rest/api/user/current` (`type` 이 `known`) |

## 1. 토큰 발급

1. 크롬에서 해당 사이트에 로그인(OTP) — `https://ecody-ims.autoever.com` 또는 `https://ecody-ecm.autoever.com`
2. 우측 상단 프로필 아이콘 → **프로필**(Jira) / **설정**(Confluence)
3. 왼쪽 메뉴 **개인 액세스 토큰**(Personal Access Tokens) → **토큰 생성**(Create token)
4. 이름 예 `claude-code`, 만료일은 사내 정책대로 → **생성**
5. 화면에 **한 번만** 보이는 값을 복사

> 메뉴가 보이지 않으면 사이트 관리자가 PAT 기능을 끈 것이다. 그때는 그 사이트만 토큰 없이(크롬 폴백) 쓰고 관리자에게 활성화를 요청한다. 아이디·비밀번호 방식은 이 스킬에서 지원하지 않는다(OTP·계정 잠금 위험).

### 현재 발급분

| 항목 | IMS | ECM |
| --- | --- | --- |
| 등록일 | 2026-11-04 | 2026-11-04 |
| 만료 | **2027-03** | **2027-03** (정확한 날짜는 프로필 > 개인 액세스 토큰 목록) |
| 계정 | 사용자 본인 계정이 아닌 공용 계정 | 같음 |

만료가 가까워지면(2027-02 중) 미리 재발급해 `setx` 로 덮어쓴다. 만료 뒤에는 `check` 가 `HTTP 401` 을 낸다 — 토큰 문제이지 사내망·권한 문제가 아니다.

## 2. 환경변수 등록

```powershell
setx ECODY_IMS_TOKEN "<IMS 토큰>"
setx ECODY_ECM_TOKEN "<ECM 토큰>"
```

- `setx` 는 **새로 여는 터미널부터** 적용된다. 이미 떠 있는 Claude Code 세션에서 바로 쓰려면 명령 앞에 붙인다:

```powershell
$env:ECODY_ECM_TOKEN=[Environment]::GetEnvironmentVariable('ECODY_ECM_TOKEN','User'); python <스킬폴더>\scripts\ecm_api.py check
```

- 선택 환경변수(`<SITE>` 는 `IMS`·`ECM`): `ECODY_<SITE>_URL`(기본 각 사이트 주소), `ECODY_<SITE>_INSECURE=1`(인증서 오류 시), `ECODY_<SITE>_NOPROXY=1`(프록시 무시).
- 토큰은 사용자 환경변수에 평문으로 저장된다. 만료·PC 반납·퇴사 시 각 사이트 프로필에서 토큰을 **폐기(Revoke)** 한다.
- 토큰 값은 화면·대화·커밋에 출력하지 않는다. 스크립트도 출력하지 않는다.

## 3. 등록 확인

```powershell
python <스킬폴더>\scripts\ims_api.py check
python <스킬폴더>\scripts\ecm_api.py check
```

`IMS_CHECK OK (환경변수 ECODY_IMS_TOKEN) : <계정명> / … ` 처럼 계정이 나오면 끝이다.

| 결과 | 뜻 | 할 일 |
| --- | --- | --- |
| `TOKEN_MISSING` | 환경변수가 비어 있음 | 2절 등록, 또는 그 사이트만 크롬 폴백 |
| `HTTP 401` | 토큰 만료·무효 | 1절로 재발급 |
| `ECM_CHECK FAIL … type=anonymous` | 토큰이 먹지 않음(헤더 누락·PAT 비활성) | 토큰 재발급, 안 되면 크롬 폴백 |
| `HTTP 403` | 권한 없음(계정·IP 제한) | 사내망 여부 확인, 관리자 문의 |
| `URLError`/`SSLError` | 사내망 밖, 프록시·인증서 문제 | VPN 연결, `ECODY_<SITE>_NOPROXY=1` / `ECODY_<SITE>_INSECURE=1` 시도 |
