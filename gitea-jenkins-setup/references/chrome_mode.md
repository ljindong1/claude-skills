# Chrome 모드 (API 토큰이 없을 때)

`preflight`의 `mode`가 `chrome`인 시스템만 이 방식으로 처리한다. 한쪽만 토큰이 있으면 그쪽은 API로 한다.
로컬 git 단계(clone·branch·add-bat)와 `detect-project`, `render-job`은 모드와 무관하게 항상 `gjsetup.py`로 한다.

## 0. 준비

- Claude in Chrome 도구(`mcp__claude-in-chrome__*`)가 있는지 확인한다. 없으면 사용자에게
  "Claude Code에서 Chrome 연동을 켜고(`/chrome`) 브라우저에서 Gitea·Jenkins에 로그인해 두라"고 안내하고 중단한다.
- `tabs_context_mcp`로 탭을 만들고, 대상 사이트로 이동해 **로그인 상태인지** 먼저 확인한다
  (Gitea 우측 상단 사용자 메뉴, Jenkins 우측 상단 사용자 아이콘). 로그인이 안 되어 있으면 사용자에게 로그인을 요청한다.
- 페이지 안 JavaScript 실행은 사용자의 로그인 세션을 쓴다. 조회는 `fetch` GET으로, 생성은 아래 절차로 한다.
- 규칙은 API 모드와 같다: **생성만, 수정·삭제 금지.** 이미 있으면 비교해서 재사용하거나 보고만 한다.
- 작업이 끝나면 만든 탭을 닫는다.

## 1. Gitea

### 1.1 조회 (공통)

Gitea API는 세션 쿠키로는 401이 난다. 웹 경로를 쓴다.

```javascript
// 로그인 ID
const me = [...document.querySelectorAll('.user-menu .header, .dropdown .header')]
  .map(e => e.textContent.trim()).join(' ');           // "다음 사용자로 로그인됨 jdlee" 형태
// 저장소 존재 여부
const exists = (await fetch('/<owner>/<repo>')).status === 200;
// 브랜치 목록 (파일 목록 API와 같은 경로)
const html = await fetch('/<owner>/<repo>/branches').then(r => r.text());
const branches = [...new DOMParser().parseFromString(html, 'text/html')
  .querySelectorAll('a.gt-ellipsis, .branch-name')].map(a => a.textContent.trim());
// 서브모듈
const gm = await fetch('/<owner>/<repo>/raw/branch/<branch>/.gitmodules');
```

비공개 저장소 파일 내용은 인증 정보가 섞여 있으면 도구가 출력을 가릴 수 있다. 내용 대신 존재 여부·줄 수만 확인한다.

### 1.2 Fork

1. `/<me>/<repo>`가 이미 있으면: 페이지 상단의 포크 원본 표시가 `<원본 owner>/<repo>`인지 확인 → 맞으면 재사용, 아니면 conflict 보고 후 중단.
2. 없으면 `/<원본 owner>/<repo>/fork`로 이동해 화면 입력:
   - **소유자**: 본인 계정 (표시 이름으로 보임) 또는 랩 공용이면 해당 조직
   - **리포지토리 이름**: 원본과 같게
   - **포크로 클로닝될 브랜치**: **모든 브랜치**
   - **설명**: 과제 설명 (선택)
   - **리포지토리 포크** 클릭
3. 확인: `/<me>/<repo>` 200, 브랜치 목록에 기준 브랜치 포함.

### 1.3 공동작업자 (`build` 쓰기)

1. `/<me>/<repo>/settings/collaboration`으로 이동해 목록을 읽는다.
   - `build (빌드서버 계정)` 줄이 이미 있고 권한이 **쓰기** 이상이면 재사용.
   - 있는데 **읽기**면 수정하지 않고 conflict로 보고한다 (사용자가 직접 변경).
2. 없으면 **새 공동작업자 추가** 입력칸에 `build` 입력 → 목록에서 `build (빌드서버 계정)` 선택 → 추가.
3. 방금 추가한 줄의 권한이 쓰기가 아니면 드롭다운에서 **쓰기**로 바꾼다 (skill이 방금 만든 항목이므로 허용).
   `제거`는 절대 누르지 않는다.
4. 확인: 목록에 `build … 쓰기`.

## 2. Jenkins

`render-job`으로 만든 XML 파일 내용을 읽어 JavaScript 문자열로 넣는다(`JSON.stringify` 결과를 그대로 붙인다).
Jenkins 페이지(`<JENKINS_URL>/`)가 열린 탭에서 실행한다.

### 2.1 조회

```javascript
const crumb = await fetch('/crumbIssuer/api/json').then(r => r.json());
const exists = (await fetch('/job/<JOB>/api/json?tree=name')).status === 200;
const views = (await fetch('/api/json?tree=views[name]').then(r => r.json())).views.map(v => v.name);
// 인증정보 ID 후보: 운영 중인 참고 Job에서 읽기만 한다
const ref = await fetch('/job/<REF_JOB>/config.xml').then(r => r.text());
const credIds = [...new Set([...ref.matchAll(/<credentialsId>([^<]+)<\/credentialsId>/g)].map(m => m[1]))];
```

### 2.2 Job 생성 (비활성)

```javascript
if ((await fetch('/job/<JOB>/api/json?tree=name')).status === 200) throw 'conflict: Job exists';
const c = await fetch('/crumbIssuer/api/json').then(r => r.json());
const xml = <렌더된 XML 문자열>;
const r = await fetch('/view/<VIEW>/createItem?name=' + encodeURIComponent('<JOB>'), {
  method: 'POST',
  headers: { 'Content-Type': 'application/xml; charset=utf-8', [c.crumbRequestField]: c.crumb },
  body: xml
});
r.status;   // 200 또는 302면 성공. 뷰가 없으면 경로에서 '/view/<VIEW>'를 뺀다
```

### 2.3 검증

```javascript
const cx = await fetch('/job/<JOB>/config.xml').then(r => r.text());
const d = new DOMParser().parseFromString(cx, 'text/xml');
const t = s => [...d.getElementsByTagName(s)].map(e => e.textContent);
({
  url: t('url'), branch: t('name'), exclusion: t('excludedMessage').map(v => JSON.stringify(v)),
  spec: t('spec'), cmd: t('command'), disabled: t('disabled'),
  choices: t('string'), perms: t('permission').filter(p => p.endsWith(':<USER>'))
})
```

통과 기준은 SKILL.md 6단계 표와 같다. 특히 `exclusion`이 정확히 `"(?s).*Auto commit from Jenkins.*"`(앞뒤 공백 없음)여야 한다.

### 2.4 활성화 (사용자가 원할 때만)

```javascript
const c = await fetch('/crumbIssuer/api/json').then(r => r.json());
(await fetch('/job/<JOB>/enable', { method: 'POST', headers: { [c.crumbRequestField]: c.crumb } })).status;
```
