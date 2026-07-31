# Phase A — 전수 소인 절차 (P2~P5)

> **이 단계에서는 관련성을 일절 판단하지 않는다.** 읽고, 담고, 원장에 기록한다. 판단은 P6에서만 한다.

## 0. 도구 로드

deferred 상태이므로 먼저 불러온다. 한 번의 `tool_search` 호출에 몰아서 로드한다.

```
tool_search("select:mcp__Slack__slack_read_channel,mcp__Slack__slack_read_thread,mcp__Slack__slack_search_public_and_private,mcp__Slack__slack_send_message,mcp__Slack__slack_search_users,mcp__Slack__slack_search_channels")
```

## 1. 도구 실측 제약 (2026-07-31 측정 — 절차가 이렇게 생긴 이유)

| # | 실측 결과 | 함의 |
| --- | --- | --- |
| C1 | `slack_search_public` 은 비공개 채널을 **못 본다** | `#모베이스에이에쓰이씨-공통`(비공개)은 공개 검색으로 영원히 안 잡힌다 |
| C2 | `search_public_and_private(query="in:<#C09GSH1MBSS>")` → **0건**. `query="from:<@U09L8G19BF0>"` → **0건** | **modifier만으로는 채널 전수 열람이 불가능.** 검색어(term)가 반드시 있어야 한다 |
| C3 | `slack_read_channel(id, oldest, latest)` → 창 안 전건 반환 | **완전수집의 유일한 수단** |
| C4 | `search_public_and_private(query="니다", only_my_channels=true, after=…)` → 비공개 포함 전 채널에서 히트 | **소스 발견용으로 유효**. 단 반말·명사종결·파일전용 메시지는 샐 수 있어 완전수집용은 아니다 |
| C5 | `slack_search_channels(channel_types="public_channel,private_channel")` → 비공개 포함 카탈로그를 커서 페이징으로 열거 | 레지스트리 점검용 |
| C6 | 검색 결과는 페이지당 최대 20건 + `cursor` | 20건이 꽉 차면 **반드시 다음 페이지를 넘긴다** |

> **결론: 채널 수집을 검색에 맡기면 구조적으로 샌다.** C2 때문에 채널을 통째로 훑는 검색 질의가 존재하지 않는다. `read_channel` 전수 호출이 유일한 답이다.

## 2. 원장(ledger) 초기화 — P2

```bash
python3 scripts/context.py init --window-start <창시작 unix초>
```

`sources.json`의 채널 + DM 로스터 + `self` 를 모두 `pending` 으로 등록한 `ledger.json`을 만든다. 이후 소스를 하나 끝낼 때마다:

```bash
python3 scripts/context.py mark --source <소스 id> --count <수집 건수>
```

## 3. 채널 전수 소인 — P3

`sources.json`의 **모든** 채널에 대해 (tier 무관, core도 watch도 전부):

```
slack_read_channel(
  channel_id = "<id>",
  oldest     = "<창시작 unix초>",
  limit      = 100,
  response_format = "concise"
)
```

- `pagination_info`에 다음 커서가 있으면 **끝까지 넘긴다.** 첫 페이지만 읽고 끝내지 않는다.
- 결과가 0건이어도 정상이다. `mark --count 0` 으로 소인 완료 처리한다. **읽지 않은 것과 읽었는데 비어 있는 것은 다르다** — 원장이 그 차이를 기록한다.
- `Reply count`가 붙은 메시지는 스레드 답글까지:
  ```
  slack_read_thread(channel_id="<id>", message_ts="<부모 ts>")
  ```
- **첨부파일명을 본문과 동등하게 취급한다.** 일정·요청이 파일명에만 인코딩된 경우가 흔하다.
  예) `금_1400_고용재_AI_면접제안메일.zip` → 금요일 14:00 / `소프트웨어아키텍처설계실_소개_260730_v02.pptx` → 소개 자료 v02
  본문이 한 줄뿐이고 실체가 첨부인 메시지를 "내용 없음"으로 버리지 않는다.

## 4. DM 소인 — P3

**[1순위] 창 안의 DM 전체 검색** — 발신자를 미리 몰라도 된다.

```
slack_search_public_and_private(
  query        = "to:me",            # 대상 지정 시 "to:<@대상ID>"
  channel_types= "im,mpim",
  after        = "<창시작 unix초>",
  sort = "timestamp", sort_dir = "desc"
)
```

20건이 꽉 차면 `cursor`로 페이지를 넘긴다.

**[2순위] 로스터 직접 읽기** — 1순위와 **병행**한다(대체가 아니다). `sources.json`의 `dm_roster` 전원에 대해:

```
slack_read_channel(channel_id="<상대 user_id>", oldest="<창시작>")
```

`to:me`는 검색 인덱스에 의존하므로 첨부만 있는 DM 등을 놓칠 수 있다. 로스터 직접 읽기가 그 구멍을 막는다.

**[3순위] 로스터 밖 발신자** — 1순위 결과에 로스터에 없는 사람이 있으면 그 DM도 `read_channel`로 보강하고, 브리핑 말미에 로스터 등록을 제안한다.

## 5. 발견 스윕 (드리프트 검출) — P4

레지스트리 밖에서 벌어진 일을 잡는 단계다. `sources.json`의 `discovery_tokens` 중 **최소 3개**로:

```
slack_search_public_and_private(
  query           = "<토큰>",
  only_my_channels= true,
  after           = "<창시작 unix초>",
  sort = "timestamp", sort_dir = "desc", limit = 20,
  response_format = "concise", include_context = false
)
```

- 결과에 등장한 `channel_id` 중 `sources.json`에 **없는 것**이 있으면:
  1. 그 채널을 즉시 `read_channel`로 전수 소인한다(원장에 `discovered:<id>`로 추가).
  2. 브리핑 말미 감사 푸터에 `미등록 소스 N` 으로 표시하고, 채널명·id·건수를 한 줄 붙여 **등록을 제안**한다.
- 이 스윕이 이번 재설계의 근거다: 2026-07 사고 당시 `#proj_2026모빌진-기반-차세대-미들웨어플랫폼`, `#mobase_asec_미들웨어플랫폼_sw_개발` 두 채널이 정확히 이 방식으로 드러났다.

### 주간 레지스트리 재점검 (월요일 실행 시)

```
slack_search_channels(query="a", channel_types="public_channel,private_channel", limit=20)
```

커서로 끝까지 페이징해 카탈로그를 뽑고 `sources.json`과 대조한다. 신규 채널이 보이면 브리핑 말미에 알린다. (질의어는 임의의 흔한 문자 — 이름 매칭이 느슨해 사실상 카탈로그 열거로 동작한다.)

## 5.5. 소스 수명주기 — 생성·아카이브·소멸 처리

채널은 생기고, 조용해지고, 아카이브되고, 사라진다. 각 전이를 이렇게 처리한다. (아래 동작은 2026-07-31 실측 확인.)

| 상황 | `slack_read_channel` 동작 | 처리 |
| --- | --- | --- |
| **신규 채널** | 정상 | 발견 스윕(P4)이 잡는다 → `add --discovered` → 소인 → 푸터에 등록 제안 |
| **아카이브됨** | ✅ **성공, 항상 0건** | 게이트를 막지 않는다. `mark --count 0`. 30일 연속 0건이면 `retired_channels` 이동 제안 |
| **삭제 / 이탈 / id 오기** | ❌ `channel_not_found` 오류 | **재시도 금지.** `mark --status unavailable --reason not_found` 로 명시 처리하고 계속 진행. 푸터에 반드시 표시 |

```bash
# 오류로 읽을 수 없는 소스 — 포기하지 말고 명시 처리한다
python3 scripts/context.py mark --source C0XXXXXXXXX --count 0 \
        --status unavailable --reason not_found
```

> **왜 오류를 pending 으로 남기지 않는가.** 게이트#1이 pending 을 막는 설계라, 소스 하나가 오류를 내면 무인 루틴에서 브리핑이 **영원히 발송되지 않는다.** 그건 원래 누락 버그보다 나쁜 조용한 전면 실패다. 접근 불가는 "해소된 상태"로 통과시키되 **반드시 보이게** 만든다 — 게이트#2가 푸터 표시 여부까지 검사한다.

`retired_channels` 에 있는 채널은 소인하지 않고, 발견 스윕이 다시 찾아내도 "미등록 소스"로 재제안하지 않는다. 해제(unarchive)되어 새 트래픽이 생기면 스윕이 잡으므로, 그때 `channels` 로 복귀시킨다.

### 레지스트리 영구 반영의 한계 (솔직히)

스킬 디렉터리는 세션에서 **읽기 전용 캐시**다. 발견한 신규 채널을 `sources.json` 에 적어도 다음 실행에는 남지 않는다. 그래서:

- 신규 채널은 **매일 재검출되고 매일 재제안된다.** 번거롭지만 **누락되지는 않는다** — 그날 브리핑에는 소인되어 들어간다.
- 제안이 반복되면 사용자가 `sources.json` 을 갱신해 스킬을 다시 저장해야 조용해진다. 푸터 문구에 그 점을 담는다.

## 6. 게이트 #1 — P5

```bash
python3 scripts/context.py gate-coverage
```

- exit 0 → P6 진행
- exit 1 → **P3으로 복귀.** 출력에 어떤 소스가 `pending`인지 나온다. 전부 `swept`가 될 때까지 다음 단계로 가지 않는다.

## 7. 수집 결과 기록 형식

Phase A의 산출물은 다음 필드를 가진 목록이다. 모델이 메모리로 들고 가도 되지만, 건수가 많으면 파일로 남긴다.

| 필드 | 설명 |
| --- | --- |
| `ts` | 슬랙 타임스탬프 |
| `source` | 채널 id 또는 DM 상대 user_id |
| `source_label` | 표시용 이름 (`🔒채널명` / `한글이름(English Name)`) |
| `author` | 작성자 한글이름(English Name) |
| `time_kst` | `M/D(요일) HH:MM` |
| `text` | 본문 (요약 전 원문) |
| `files` | 첨부파일명 목록 |
| `permalink` | 원문 링크 |
| `broadcast` | `@channel`/`@here` 여부 |
| `mentions_target` | 대상이 멘션됐는지 |
