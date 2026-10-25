# 경로 C 자동화 — 브라우저 세션으로 복사·검증·발행·첨부 복원

2026-10 실전(총 65페이지, 첨부 29파일)에서 검증된 절차다. 사람이 손으로 하면 페이지당 1~2분, 이 절차로는 약 40초.

## 0. 전제와 환경

- Claude in Chrome(`mcp__claude-in-chrome__*`)을 쓴다. **연결된 브라우저가 2개 이상이면 반드시 사용자에게 고르게 한다** — "다른 PC"의 Chrome을 골라 작업하다 그 PC 탭을 닫으면 세션이 끊긴다.
- 탭 2개를 만든다: **소스 탭**(회사 등 읽기 사이트)과 **타겟 탭**(쓰기 사이트). 둘 다 사용자가 이미 로그인된 상태여야 한다.
- 작업 중 **Chrome 창이 OS의 포그라운드(활성 창)**여야 한다. 다른 앱이 앞에 오면 `Ctrl+C`의 copy 이벤트는 발생해도 클립보드가 비어 붙여넣기 결과가 0바이트가 된다. 증상이 나오면 "Chrome 창을 한 번 클릭해 앞으로 가져와 주세요"라고 요청한 뒤 같은 동작을 재시도한다.
- 사용자에게 "작업 중에는 제가 여는 탭(탭 그룹)을 닫지 마세요"라고 미리 알린다. 그룹이 사라지면 `tabs_context_mcp`가 "no longer exists"를 돌려준다 — 새 그룹을 만들고 **발행 안 된 초안은 `edit-v2/<id>` URL로 다시 열어 이어 쓴다**(초안은 남아 있다).

### `browser_batch` 제약 (지키지 않으면 배치가 즉시 거부됨)

- 한 배치는 **한 tabId**만 다룬다.
- 배치 안에 `navigate`를 넣으면 그 뒤에 아무 동작도 못 넣는다 → **navigate는 항상 단독 호출**, 그다음 배치로 페이지 위 동작.
- `javascript_tool` 반환값에 쿠키·토큰·base64·긴 원문이 섞이면 `[BLOCKED: ...]`로 가려진다. **원문은 반환하지 말고 길이·개수·앞뒤 60자만 반환**한다. 원문은 DOM(textarea)에 두고 클립보드로 옮긴다.
- `javascript_tool`의 같은 출처 `fetch`는 **정상 동작한다**(REST 읽기, 페이지 PUT, move API 모두 OK). 막히는 건 결과 표시뿐이다.

## 1. 소스 본문 복사 (소스 탭)

```js
// navigate 단독 호출 후, 다음 배치에서:
for(let i=0;i<20;i++){ if(document.querySelector('.ak-renderer-document')) break; await new Promise(r=>setTimeout(r,500)); }
await new Promise(r=>setTimeout(r,1500));
const el=document.querySelector('.ak-renderer-document');
const r=document.createRange(); r.selectNodeContents(el);
const s=window.getSelection(); s.removeAllRanges(); s.addRange(r);
({title:document.title.replace(/ - .* - Confluence$/,''),
  n:el.innerText.replace(/\s+/g,'').length,          // 공백 제거 글자수 = 검증 기준
  imgs:el.querySelectorAll('img').length,            // 첨부 복원 대상 수
  tables:el.querySelectorAll('table').length,        // 렌더러는 sticky 헤더 때문에 표를 2배로 센다
  code:el.querySelectorAll('.code-block,pre').length,
  lists:el.querySelectorAll('ul,ol').length,
  ext:[...el.querySelectorAll('[data-extension-key]')].map(e=>e.getAttribute('data-extension-key'))})
```
이어서 같은 배치에 `computer.key ctrl+c`.

- `document.title`에서 얻은 제목이 **실제 제목**이다. URL 슬러그(예: `SW+Tools`)는 제목이 아니다(실제 제목은 "임베디드SW 개발 Tools"였음).
- 제목의 `&amp;`는 원본 저장 오류이므로 `&`로 바로잡고 완료 보고에 적는다.

## 2. 타겟 페이지 생성·붙여넣기·검증 (타겟 탭)

```
navigate → https://<타겟host>/wiki/create-content/page?spaceKey=<KEY>&parentPageId=<부모ID>
```
부모는 **페이지든 폴더든** `parentPageId`에 넣으면 된다. 그 뒤 배치:

```js
// 1) 에디터 로드 대기
for(let i=0;i<30;i++){ if(document.querySelector('.ProseMirror') && document.querySelector('textarea[placeholder*="제목"]')) break; await new Promise(r=>setTimeout(r,500)); }
await new Promise(r=>setTimeout(r,1500)); location.href   // edit-v2/<draftId> 확인
```
`find`로 제목 textbox·본문 textbox ref를 얻고, 한 배치로 **제목 클릭 → type 제목 → 본문 클릭 → ctrl+v** 한 뒤 검증:

```js
await new Promise(r=>setTimeout(r,2000));
const pm=document.querySelector('.ProseMirror'); const doc=pm.pmViewDesc.node;   // ProseMirror 문서 모델
let tables=0,code=0,lists=0;
doc.descendants(n=>{ if(n.type.name==='table') tables++; if(n.type.name==='codeBlock') code++;
  if(n.type.name==='bulletList'||n.type.name==='orderedList') lists++; });
({title:document.querySelector('textarea[placeholder*="제목"]').value,
  n:doc.textContent.replace(/\s+/g,'').length, tables, code, lists, tail:doc.textContent.slice(-40)})
```

**검증 기준**: 제목 일치, `n`이 소스와 ±5% 이내(이미지 자리의 "미리 보기를 사용할 수 없음" 문구만큼 늘 수 있음), `tables`가 소스의 **절반**, `code`·`lists` 동일, `tail`이 원본 끝문장. 긴 코드블록은 에디터 DOM이 가상 스크롤로 일부만 그리므로 **DOM이 아니라 문서 모델로** 센다(74줄 코드블록이 DOM에선 '31,32…' 줄번호만 보였다).

- 제목을 먼저 치고 본문을 붙이는 순서가 안전하다. 본문 먼저 붙이고 제목 textarea를 JS `focus()`로 잡으면 제목이 본문에 들어간다(`ctrl+z`로 복구 가능).
- 붙여넣기 결과 `n:0`이면 클립보드 문제(§0 포그라운드)다.

## 3. 발행

```js
// '게시...' 버튼은 find로 ref를 얻어 클릭(헤더 ref는 페이지마다 바뀐다). 그다음:
let b; for(let i=0;i<60;i++){ b=[...document.querySelectorAll('[role=dialog] button')].find(x=>x.innerText.trim()==='게시'); if(b) break; await new Promise(r=>setTimeout(r,500)); }
if(!b) throw new Error('publish dialog not found');
await new Promise(r=>setTimeout(r,800)); b.click();
for(let i=0;i<30;i++){ if(!location.href.includes('edit-v2')) break; await new Promise(r=>setTimeout(r,500)); }
location.href    // /pages/<새ID>/… 로 바뀌면 발행 완료. 이 숫자가 새 페이지 ID
```
- 다이얼로그가 느리게 뜨면 'not found'가 난다 → 스크린샷으로 떠 있는지 보고, 떠 있으면 좌표 클릭(화면 1463×812 기준 (969,349) 부근)으로 확정한다.
- `edit-v2` URL이 그대로면 발행이 안 된 것. 흔한 원인: **스페이스 내 제목 중복**(Confluence는 스페이스 전체에서 제목이 고유해야 한다). 좌하단에 "페이지에 고유한 이름을 지정하세요" 플래그가 뜬다 → 사용자에게 접미어를 제안해 고르게 한다(예: "타입 힌트 (python-dev)"). **시작 전에 전 제목을 미리 검사**하면 이걸 피한다:
  `fetch('/wiki/rest/api/content?spaceKey=<KEY>&type=page&title='+encodeURIComponent(t))` → `size>0`이면 충돌.

## 4. 트리 생성 순서와 이동

- 루트 → 1단계 → 2단계 순으로 만들고 `원본ID→새ID` 표를 유지한다. 자식은 부모의 **새 ID**를 parentPageId로 쓴다.
- 부모를 잘못 둔 페이지는 다시 만들지 말고 **이동**한다(ID 유지, 자식은 따라온다):
  `fetch('/wiki/rest/api/content/<pageId>/move/append/<새부모ID>',{method:'PUT',headers:{'X-Atlassian-Token':'no-check'}})` → 200.
- 폴더 생성은 만들기 메뉴 → 폴더 → 제목 클릭 → ctrl+a → 입력 → Enter. 새 폴더 ID는 URL `/folder/<id>`.
- 끝나면 구조 검증: `fetch('/wiki/api/v2/pages/<루트ID>/descendants?limit=250&depth=5')`로 parentId별 개수를 소스와 대조한다. 페이지 수는 이 API로 세어 보고한다(암산하면 틀린다).

## 5. 첨부 이미지 복원 (SVG·PNG 모두 가능)

클립보드 복사 직후 본문의 이미지 노드는 `ri:filename="Invalid file id - …"`로 깨져 있다("미리 보기를 사용할 수 없음"). 원본 첨부를 **같은 파일명**으로 업로드하고 참조를 바꿔 주면 살아난다.

### 5.1 대상 파악 (소스 탭)
```js
// 본문에 실제로 쓰인 이미지만 — 첨부 목록 전체가 아니다 (.skill·pdf·exe 등 자료 첨부는 제외)
const pg=await (await fetch(`/wiki/api/v2/pages/${srcId}?body-format=storage`)).json();
[...pg.body.storage.value.matchAll(/<ac:image[^>]*>\s*<ri:attachment[^>]*ri:filename="([^"]+)"/g)].map(m=>m[1])
```
같은 페이지에서 `/wiki/rest/api/content/${srcId}/child/attachment?limit=50`으로 첨부 id·mediaType·fileSize를 얻는다.

### 5.2 패킹 → 클립보드 (소스 탭, 한 번 정의해 두고 재사용)
```js
window.__pack = async function(pageId, names){
  const list=(await (await fetch(`/wiki/rest/api/content/${pageId}/child/attachment?limit=50`)).json()).results;
  const files=[];
  for(const n of names){
    const a=list.find(x=>x.title===n); if(!a) throw new Error('missing '+n);
    const r=await fetch('/wiki'+a._links.download); const type=a.extensions.mediaType; let data,enc;
    if(type==='image/svg+xml'){ data=await r.text(); enc='text'; }
    else { const buf=new Uint8Array(await r.arrayBuffer()); let s='';
      for(let i=0;i<buf.length;i+=0x8000) s+=String.fromCharCode.apply(null,buf.subarray(i,i+0x8000));
      data=btoa(s); enc='b64'; }
    files.push({name:n,type,enc,data,size:a.extensions.fileSize});
  }
  const payload=JSON.stringify({pageId,files});
  let ta=document.getElementById('__xfer'); if(!ta){ ta=document.createElement('textarea'); ta.id='__xfer';
    ta.style.cssText='position:fixed;top:0;left:0;z-index:99999'; document.body.appendChild(ta); }
  ta.value=payload; ta.focus(); ta.select();
  return {len:payload.length, files:files.map(f=>f.name+':'+f.size)};   // 원문은 반환하지 않는다
};
await window.__pack('<srcId>', ['a.svg','b.png'])
```
이어서 `computer.key ctrl+c`. 2MB급 PNG도 base64로 무리 없이 넘어갔다.

### 5.3 업로드 + 참조 연결 (타겟 탭)
REST `POST .../child/attachment`는 브라우저 세션에서 **XSRF 403**이 난다(`X-Atlassian-Token`·`atl_token` 어느 쪽도 안 됨). 대신 **페이지의 "첨부 파일" 화면 폼**을 쓴다 — 폼이 토큰을 들고 있다.

```
navigate → https://<타겟host>/wiki/pages/viewpageattachments.action?pageId=<새ID>
```
```js
// 폼 대기 → textarea 생성·포커스 → (배치 안에서) ctrl+v → 아래 함수 호출
window.__restore = async function(targetId){
  const p=JSON.parse(document.getElementById('__xfer').value);
  const form=document.querySelector('form[action*=doattachfile]');
  const tok=form.querySelector('input[name=atl_token]').value; const results=[];
  for(const f of p.files){
    let blob; if(f.enc==='text') blob=new Blob([f.data],{type:f.type});
    else { const bin=atob(f.data); const u8=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i); blob=new Blob([u8],{type:f.type}); }
    const fd=new FormData(); fd.append('atl_token',tok); fd.append('file_0',new File([blob],f.name,{type:f.type}));
    fd.append('comment_0',''); fd.append('confirm','첨부');
    const r=await fetch(form.action,{method:'POST',body:fd,credentials:'include'}); await r.text(); results.push(f.name+':'+r.status);
  }
  const list=(await (await fetch(`/wiki/rest/api/content/${targetId}/child/attachment?limit=50`)).json()).results.map(a=>a.title+' '+a.extensions.fileSize);
  const pg=await (await fetch(`/wiki/api/v2/pages/${targetId}?body-format=storage`)).json();
  let s=pg.body.storage.value, i=0;
  // 깨진 참조를 본문 등장 순서대로 파일명에 대응 — names 순서는 5.1에서 뽑은 순서 그대로
  s=s.replace(/(<ac:image[^>]*>\s*<ri:attachment[^>]*ri:filename=")Invalid file id[^"]*(")/g,(m,a,b)=>{ const n=p.files[i++]?.name; return n? a+n+b : m; });
  const put=await fetch(`/wiki/api/v2/pages/${targetId}`,{method:'PUT',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:targetId,status:'current',title:pg.title,body:{representation:'storage',value:s},version:{number:pg.version.number+1,message:'첨부 이미지 연결 (cross-site copy)'}})});
  return {uploads:results, replaced:i, expected:p.files.length, att:list, put:put.status};
};
```
**검증**: `att`의 파일 크기가 원본 fileSize와 같고, `replaced===expected`, `put===200`. 페이지 버전이 1 올라간다. 마지막에 트리 전체를 돌며 `Invalid file id`가 0건인지 확인한다.

주의 — `<ac:image>`만 바꾼다. `.skill`·pdf 같은 **파일 매크로**(`<ac:parameter>` 안의 `ri:attachment`)도 같은 "Invalid file id" 문자열을 쓰므로 정규식 범위를 넓히면 그쪽까지 SVG 파일명으로 덮어쓴다(실제 사고 1회, 되돌림). 자료 첨부는 사용자가 원하면 같은 폼으로 올릴 수 있지만 base64 경유라 수십 MB 파일은 피한다.

## 6. 보고 리듬

페이지마다 `✅ N/총 제목 → 새ID (이미지 k)` 한 줄, 묶음(1단계·각 부모의 하위)이 끝나면 한 번 더 요약. 사용자는 진행이 안 보이면 불안해한다.
