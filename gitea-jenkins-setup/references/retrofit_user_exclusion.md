# 이미 만들어진 Job 손보기 — 2겹 방어 넣기 · 폴링 끄기

**사용자가 요청할 때만 한다.** SKILL.md 절대 규칙 2(생성만 한다)의 예외이고, `migrate_to_shared_fork.md` 와 같은 성격이다. 계획을 보여 주고 승인받은 뒤에만 실행한다.

왜 필요한지는 SKILL.md 5단계의 ⚠️ **자기 커밋 루프**를 먼저 읽는다. 요지: 폴링 범위에 Jenkins 자신의 커밋 1개가 상시 장전돼 있고, 2026-11 이전에 만든 Job 은 메시지 필터 **한 겹**뿐이다.

## 무엇을 고르는가

| 안 | 바꾸는 곳 | 효과 | 대가 |
| --- | --- | --- | --- |
| **1. 폴링 끄기** | Job: Poll SCM 해제 | 트리거 경로 자체가 사라져 **완전 차단**. 장전된 커밋도 무력화 | push 자동 빌드가 없어진다. "파라미터와 함께 빌드"로 직접 실행 |
| **2. 산출물 브랜치 분리** | `GitPush.bat` `PUSH_BRANCH` + Job Branch Specifier 를 정확한 이름으로 | 작업 브랜치에 Jenkins 커밋이 안 들어와 **루프가 원리적으로 불가능**. 자동 빌드 유지 | 산출물을 받을 브랜치가 달라진다. 작업 브랜치를 새로 만들 때마다 Job 이름도 고쳐야 한다(와일드카드 상실) |
| **3. 2겹 방어** | Job: 사용자 제외 필터 + 저장소: `GitPush.bat` 신원 | 두 필터가 **동시에** 풀려야 빌드된다. 비용 거의 없음 | 같은 종류의 안전장치라 원리적 차단은 아니다 |

1 또는 2 를 고르더라도 **3 은 같이 해 둔다.** 나중에 폴링을 다시 켤 때 2겹 상태로 켜진다.

## ⚠️ 3 안은 두 변경이 짝으로 맞아야 효과가 생긴다

- Job 에 `excludedUsers = jenkins` 를 넣는 것만으로는 **아무 효과가 없다.** 커밋 신원이 아직 사람 ID 면 걸릴 것이 없다.
- 저장소의 `Build\GitPush.bat` `[USER]` 두 줄을 바꾸고 **그 작업 브랜치에 커밋·push** 해야 다음 빌드부터 발효된다(Jenkins 는 원격을 체크아웃한다).

```bat
set "COMMIT_NAME=jenkins"
set "COMMIT_EMAIL=jenkins@mobaseasec.com"
```

Job 이 여러 저장소에 걸쳐 있으면 **저장소마다** 이 두 줄을 바꿔야 한다. "Job 6개에 필터를 걸었다"는 기록만 남고 실제 방어는 bat 을 고친 저장소에서만 생기는 상태를 만들지 말 것 — 어디까지 됐는지 사용자에게 분명히 보고한다.

## `config.xml` POST 는 쓰지 않는다

일반 계정은 Job 설정 쓰기가 막혀 있다. **수정하지 않은 원본을 그대로 올려도 HTTP 500** 이 난다(2026-11-09, 2026-11-25 실측). 응답은 Jenkins 오류 페이지(`Oops! A problem occurred ... Logging ID=...`)이고 머리말이 `Sign in` 으로 렌더된다.

2026-11-25 에 6개 Job 중 `NQ6e_PSU_FBL_jdlee` 하나만 200 으로 반영되고 5개가 500 이었다 — 권한(6개 모두 동일)·XML 내용·순서로 설명되지 않았다. **신뢰할 수 없으므로 설정 화면 경로를 쓴다.** 실패한 POST 는 설정을 바꾸지 않았다(검증값 그대로였다).

## 설정 화면 경로 (2026-11-25 Job 6개로 검증)

`mcp__claude-in-chrome__*` 로 `/job/<Job>/configure` 를 열고 폼을 고친 뒤 Save 를 누른다. Jenkins 가 사람의 조작으로 받는 경로라 그대로 저장된다.

### 함정

| 함정 | 대응 |
| --- | --- |
| **navigate 직후 같은 호출에서 JS 를 돌리면 못 찾는다** | Jenkins 가 SCM 섹션을 늦게 그린다. 같은 호출 안의 `sleep 1800ms` 로도 부족했다. **navigate 와 조작 JS 를 다른 호출로 분리**한다. 한 메시지에 여러 Job 을 넣을 때는 `[앞 Job 조작 JS] + [다음 Job navigate]` 순서로 짝지어 보낸다 |
| Add 버튼을 부모 8단계까지 올려 찾으면 **매개변수 Add** 를 잡는다 | `button.hetero-list-add` 중 부모를 **6단계까지만** 올려 `Repository URL` 이 보이는 것을 고른다 |
| 로케일이 한국어여도 메뉴 항목은 영문 | 정확히 `Polling ignores commits from certain users` |
| 값에 이메일을 넣으면 안 걸린다 | 이 필터는 **커밋 작성자 이름**으로 비교한다. 값은 `jenkins` |
| Save 를 누르면 페이지가 이동해 JS 평가가 끊긴다(`Inspected target navigated`) | 정상이다. Save 클릭까지 한 호출에서 끝내고, **다음 호출에서 `config.xml` 로 검증**한다 |
| Save 직후 곧바로 다른 곳으로 navigate 하면 POST 가 취소될 수 있다 | Save 한 호출과 다음 navigate 사이에 최소 한 번의 왕복을 둔다. 끝나고 전수 검증해 빠진 Job 을 다시 처리한다 |

### 조작 JS 골격

```js
// 1) 폴링 끄기 (1안일 때만)
const poll = document.querySelector('input[name="hudson-triggers-SCMTrigger"]');
if (poll.checked) poll.click();

// 2) 사용자 제외 필터 추가 (3안)
let btn = null;
for (const b of [...document.querySelectorAll('button.hetero-list-add')]) {
  let n = b;
  for (let k = 0; k < 6 && n; k++) { n = n.parentElement; if (n && /Repository URL/.test(n.innerText || '')) { btn = b; break; } }
  if (btn) break;
}
btn.click(); await new Promise(r => setTimeout(r, 900));
[...document.querySelectorAll('.jenkins-dropdown__item, [role=menuitem]')]
  .find(e => e.innerText.trim() === 'Polling ignores commits from certain users').click();
await new Promise(r => setTimeout(r, 1000));
const t = document.querySelector('[name="_.excludedUsers"]');
t.value = 'jenkins';
t.dispatchEvent(new Event('input', {bubbles:true}));
t.dispatchEvent(new Event('change', {bubbles:true}));

// 3) 저장 전 점검 — 하나라도 어긋나면 Save 하지 않는다
//    _.excludedMessage 유지 / _.url 유지 / parameter.name === 'BuildType' / poll 의도대로
document.querySelector('button[name="Submit"]').click();
```

이미 `[name="_.excludedUsers"]` 가 있으면 **건드리지 않고 건너뛴다**(`skip`).

### 저장 후 검증

`/job/<Job>/config.xml` 을 GET 해서 확인한다. 바뀌면 안 되는 것까지 함께 본다.

```
excludedUsers   = jenkins
excludedMessage = (?s).*Auto commit from Jenkins.*   (유지)
triggers        = <triggers/>            (1안) 또는 <spec>* * * * *</spec> (유지)
url · BranchSpec · command · BuildType · disabled   (전부 유지)
```

## 2026-11-25 적용 현황 (jdlee Job 6개)

| Job | 폴링 | 사용자 제외 | 저장소 `GitPush.bat` |
| --- | --- | --- | --- |
| HE1i_PSU_AUTOSAR_jdlee | **해제** | `jenkins` | `tglee/psu_master` — 수정됨(커밋은 사용자 지시 대기) |
| HE1i_PSU_FBL_jdlee | 유지 | `jenkins` | `tglee/psu_fbl_master` — **미반영** |
| NQ6e_PSU_AUTOSAR_jdlee | 유지 | `jenkins` | `tglee/psu_master` (같은 저장소, 다른 브랜치) |
| NQ6e_PSU_FBL_jdlee | 유지 | `jenkins` | `tglee/psu_fbl_master` — **미반영** |
| LT2_TPMS_AUTOSAR_jdlee | 유지 | `jenkins` | `Kahuz/tpms_rf_receiver_bj` — **미반영** |
| LT2_TPMS_FBL_jdlee | 유지 | `jenkins` | `Kahuz/tpms_rf_receiver_bj_fbl` — **미반영** |

미반영 저장소는 그 과제를 작업할 때 두 줄을 고친다. 그 전까지 해당 Job 은 **1겹**이다.
