# Jenkins 앞단의 SSO 프록시 — API 가 막히는 이유

**2026-11-25 서울사무소에서 실측.** `JENKINS_URL` 로 CLI 에서 토큰을 써서 호출하면 전부 302 로 되돌려진다. **토큰 문제가 아니므로 재발급하지 말 것.**

## 젠킨스는 문이 두 개다

같은 젠킨스 한 대에 주소가 둘 붙어 있다. `wiki...:5151` 로 들어가 Job 의 `api/json?tree=url` 을 읽으면 젠킨스가 자기 주소를 `http://build.mobaseelec.com:8800/` 로 답한다 — 안에 있는 것은 같은 인스턴스다.

| | `https://wiki.mobaseelec.com:5151` | `http://build.mobaseelec.com:8800` |
| --- | --- | --- |
| 정체 | 대문 — Caddy 리버스 프록시 + **authentik SSO** | **젠킨스 본체**가 직접 듣는 포트 |
| IP | `211.45.175.68` (**공인**, authentik 서버와 같은 IP) | `172.23.50.2` (**사설**) |
| 인증 | **authentik 세션 쿠키**. 젠킨스 API 토큰은 젠킨스에 닿지도 않는다 | 젠킨스 자체 인증 — ID/비밀번호, **API 토큰** |
| 서울사무소에서 | 열림 (단 SSO 통과 필요 = 크롬) | **닫힘** — 핑 무응답, 포트 timeout |
| 평촌 연구소에서 | 열릴 것 | **열릴 것** (사내망 직접) |

같은 `172.23.50.x` 안에서도 Gitea(`172.23.50.4:3000`)는 서울에 **열려 있고** 젠킨스(`.2:8800`)는 **닫혀 있다** — 방화벽이 서비스별로 열어 준 상태다. 그래서 Gitea 는 API 로 되고 젠킨스는 안 된다.

## 증상 알아보기

```
/api/json  /crumbIssuer/api/json  /job/*/config.xml  /login  /me/api/json
   → 전부 302 → https://sdvsoft.cafe24.com:5454/application/o/authorize/...
   → 토큰을 붙인 응답과 안 붙인 응답의 헤더가 같다
   → 응답 헤더에 Via: 1.1 Caddy / X-Powered-By: authentik
```

`urllib`·`curl -L` 처럼 리다이렉트를 따라가면 **authentik 로그인 화면을 200 으로 받는다.** `preflight` 의 `jenkins.http` 가 200 인데 `id` 가 없으면 이것이다 — 성공으로 읽지 말 것.

## 언제부터인가

세션 기록의 `preflight` 결과가 남아 있다.

| 날짜 | `jenkins` | `mode.jenkins` |
| --- | --- | --- |
| 2026-11-06 | `http:200, id:"jdlee"` | **api** |
| 2026-11-10 | `http:200, id:"jdlee"` | **api** |
| 2026-11-24 | `http:200` (id 없음) | chrome |
| 2026-11-25 | `http:200` (id 없음) | chrome |

https 자체는 새것이 아니다 — 2026-09-17 판 `token_guide.md` 에 이미 `JENKINS_URL=https://...:5151` 이 있다. 새로 끼워진 것은 **authentik 게이트뿐**이다. 다만 11-06·11-10 에 된 이유는 둘 중 하나이고 **가리지 못했다** — (A) 11-10 이후 authentik 추가, (B) 그때는 평촌이라 사내 주소로 풀려 프록시를 지나지 않음.

## 되살리는 길

| 방법 | 내용 | 비고 |
| --- | --- | --- |
| **방화벽 (권고)** | `172.23.50.2:8800` 을 사무소에서 접근하도록 열어 달라고 요청 | Gitea 가 이미 같은 식으로 열려 있어 설명이 쉽다. 열리면 `JENKINS_URL` 만 바꿔 API 모드로 돌아간다 |
| 평촌에서 실행 | 사내망 직접 경로라 프록시가 없다 | 아래 2줄로 확인 |
| authentik 예외 | 젠킨스 앱의 `/api/*` 인증 예외 또는 토큰 인증 통과 | 서버 관리자 권한 |

평촌에서 확인하는 두 줄:

```powershell
Test-NetConnection build.mobaseelec.com -Port 8800 -InformationLevel Quiet
curl.exe -s -o NUL -w "%{http_code}`n" -u "<ID>:$env:JENKINS_TOKEN" http://build.mobaseelec.com:8800/me/api/json
```

`True` + `200` 이면 그 자리에서 API 가 된다.

## 그동안은

Chrome 모드로 한다(`references/chrome_mode.md`). 크롬에는 authentik 세션 쿠키가 있어 대문을 통과한다. **페이지 안에서 `fetch` 로 REST API 를 그대로 쓸 수 있다** — 조회는 이게 가장 빠르다.

```js
// 젠킨스 페이지(https)에서. Job 여러 개를 한 호출로 읽는다
for (const j of jobs) {
  const t = await (await fetch(`/job/${j}/config.xml`,{credentials:'include'})).text();
  // numToKeep, excludedUsers, triggers ...
}
```

막히는 것과 막히지 않는 것을 구분해 둘 것.

| | Chrome 경유 | CLI + 토큰 |
| --- | --- | --- |
| 조회(config.xml·빌드 기록·콘솔) | 된다 | 안 된다 |
| 설정 변경 | `configure` 화면 폼으로 된다 | 안 된다 |
| 빌드 실행 | 된다 | 안 된다 |
| **무인 실행**(스케줄러·배치) | **불가** — 사람이 크롬을 띄워야 한다 | 가능했을 것 |

⚠️ **`config.xml` POST 가 500 인 것은 이것과 다른 문제다.** 크롬으로 대문을 통과해 젠킨스까지 닿은 뒤 젠킨스가 거부한 것이다(크럼을 붙여도 500, 전후 바이트 동일). SSO 가 풀려도 따로 남으므로 설정 변경은 `configure` 화면으로 한다 — `references/retrofit_user_exclusion.md`.
