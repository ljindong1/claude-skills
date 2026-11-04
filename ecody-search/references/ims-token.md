# eCoDY-IMS 개인 액세스 토큰(PAT) 발급·등록

IMS 조사는 **토큰 방식이 기본**이다(크롬·OTP 세션 불필요). 토큰이 없거나 만료되면 기존 크롬 방식으로 폴백한다.

## 1. 토큰 발급 (Jira DC 10.3)

1. 크롬에서 `https://ecody-ims.autoever.com` 로그인(OTP)
2. 우측 상단 프로필 아이콘 → **프로필**(Profile)
3. 왼쪽 메뉴 **개인 액세스 토큰**(Personal Access Tokens) → **토큰 생성**(Create token)
4. 이름 예 `claude-code`, 만료일은 사내 정책대로(기본 90일 권장) → **생성**
5. 화면에 **한 번만** 보이는 값을 복사

> 메뉴가 보이지 않으면 사이트 관리자가 PAT 기능을 끈 것이다. 그때는 이 스킬을 토큰 없이 쓰고(크롬 폴백), 관리자에게 PAT 활성화를 요청한다. 토큰 대신 아이디·비밀번호를 쓰는 방식은 이 스킬에서 지원하지 않는다(OTP·계정 잠금 위험).

## 2. 환경변수 등록

```powershell
setx ECODY_IMS_TOKEN "<복사한 토큰>"
```

- `setx` 는 **새로 여는 터미널부터** 적용된다. 이미 떠 있는 Claude Code 세션에서 바로 쓰려면 명령 앞에 붙인다:

```powershell
$env:ECODY_IMS_TOKEN=[Environment]::GetEnvironmentVariable('ECODY_IMS_TOKEN','User'); python <스킬폴더>\scripts\ims_api.py check
```

- 선택 환경변수: `ECODY_IMS_URL`(기본 `https://ecody-ims.autoever.com`), `ECODY_IMS_INSECURE=1`(인증서 오류 시), `ECODY_IMS_NOPROXY=1`(프록시 무시).
- 토큰은 사용자 환경변수에 평문으로 저장된다. 만료·PC 반납·퇴사 시 IMS 프로필에서 토큰을 **폐기(Revoke)** 한다.
- 토큰 값은 화면·대화·커밋에 출력하지 않는다. 스크립트도 출력하지 않는다.

## 3. 등록 확인

```powershell
python <스킬폴더>\scripts\ims_api.py check
```

`IMS_CHECK OK (환경변수 ECODY_IMS_TOKEN) : 이진동 / jdlee / https://ecody-ims.autoever.com` 처럼 내 계정이 나오면 끝이다.

| 결과 | 뜻 | 할 일 |
| --- | --- | --- |
| `TOKEN_MISSING` | 환경변수가 비어 있음 | 2절 등록, 또는 크롬 폴백 |
| `HTTP 401` | 토큰 만료·무효 | 1절로 재발급 |
| `HTTP 403` | 권한 없음(계정·IP 제한) | 사내망 여부 확인, 관리자 문의 |
| `URLError`/`SSLError` | 사내망 밖, 프록시·인증서 문제 | VPN 연결, `ECODY_IMS_NOPROXY=1` / `ECODY_IMS_INSECURE=1` 시도 |
