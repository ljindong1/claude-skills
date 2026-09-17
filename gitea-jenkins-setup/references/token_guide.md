# API 토큰 발급 · 환경변수 등록

토큰이 없어도 skill은 Chrome 모드로 진행할 수 있다. 토큰을 등록하면 더 빠르고 결과 검증이 정확하다.

## 1. 등록할 환경변수

| 이름 | 값 (사내 기본) | 비고 |
| --- | --- | --- |
| `GITEA_URL` | `http://ccm.mobaseelec.com:3000` | 끝에 `/` 없이 |
| `GITEA_TOKEN` | Gitea 액세스 토큰 | 아래 2절 |
| `JENKINS_URL` | `https://wiki.mobaseelec.com:5151` | 끝에 `/` 없이 |
| `JENKINS_USER` | Jenkins 로그인 ID (예: `jdlee`) | |
| `JENKINS_TOKEN` | Jenkins API Token | 아래 3절 |
| `JENKINS_INSECURE` | `1` (선택) | Jenkins HTTPS 인증서 오류가 날 때만 |

## 2. Gitea 액세스 토큰

1. Gitea 로그인 → 우측 상단 프로필 아이콘 → **설정**
2. 왼쪽 **애플리케이션** → **액세스 토큰 관리** → 토큰 이름 입력 (예: `claude-code`)
3. 권한 선택: **repository: 읽기 및 쓰기**, **user: 읽기** (나머지는 선택하지 않음)
4. **토큰 생성** → 화면에 한 번만 보이는 값을 복사

## 3. Jenkins API Token

1. Jenkins 로그인 → 우측 상단 사용자 이름 → **Security** (또는 계정 → 설정)
2. **API Token** → **Add new Token** → 이름 입력 → **Generate**
3. 한 번만 보이는 값을 복사

## 4. 환경변수 등록 (PowerShell)

```powershell
setx GITEA_URL "http://ccm.mobaseelec.com:3000"
setx GITEA_TOKEN "<Gitea 토큰>"
setx JENKINS_URL "https://wiki.mobaseelec.com:5151"
setx JENKINS_USER "<Jenkins ID>"
setx JENKINS_TOKEN "<Jenkins 토큰>"
```

- `setx`는 **새로 여는 터미널부터** 적용된다. VS Code와 Claude Code를 완전히 종료 후 다시 실행한다.
- 확인: 새 PowerShell에서 `$env:GITEA_URL` (토큰 값은 화면에 출력해 확인하지 않는다).
- 토큰은 사용자 환경변수에 평문 저장된다. 퇴사·PC 반납 시 Gitea·Jenkins에서 토큰을 폐기한다.

## 5. 등록 후 점검

```powershell
python "<skill 폴더>\scripts\gjsetup.py" preflight
```

`mode`가 `{"gitea": "api", "jenkins": "api"}`이면 API 모드로 진행된다.
