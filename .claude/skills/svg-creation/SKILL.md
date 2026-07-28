---
name: svg-creation
description: SVG 파일을 생성하거나 SVG 코드를 작성할 때 항상 사용하는 스킬. 사용자가 "SVG 만들어", "SVG 파일 생성", "다이어그램 SVG", "아이콘 SVG", "SVG로 그려줘", "벡터 그래픽 만들어", ".svg 파일", "SVG 코드 작성" 등을 언급하거나, Confluence 첨부용 다이어그램·포트폴리오용 도식·문서 삽입용 그래픽처럼 SVG 산출물이 필요한 모든 상황에서 반드시 활성화하라. 인라인 svg 태그를 HTML/React 안에 작성하는 경우에도 적용된다. viewBox-only 규칙, 표준 viewBox 폭 720, 현대하모니(HDharmony) 폰트 스택, 5톤 파스텔 색상 팔레트(+밴드/존 확장 틴트), 표현 장치(액센트 바·헤더 밴드·그룹 존·번호 배지·상태 칩·hero 박스), 커넥터 3종 체계, 패턴 라이브러리(레이어 스택·파이프라인·시퀀스·상태머신·스윔레인·폴더트리), 도메인 아이콘 글리프, 시각적 여백 계산식, accessibility 태그를 강제하여 통일된 톤과 충분한 표현력을 동시에 보장한다. 이 스킬을 사용하지 않으면 톤앤매너가 깨지거나 컨테이너 의존 레이아웃 깨짐이 발생할 수 있다.
---

# SVG 파일 생성 스킬

SVG를 생성하거나 작성할 때 반드시 따라야 하는 규칙. 통일된 시각 품질(파스텔 톤), 환경 독립적 렌더링, 접근성, 그리고 **밋밋하지 않은 표현력**(§11 표현 장치, §12 커넥터)을 모두 보장한다.

## 함께 읽는 파일 (progressive disclosure)

| 파일 | 언제 읽는가 |
| --- | --- |
| `references/patterns.md` | 레이어 스택(AUTOSAR 계층도), 파이프라인/플로우, 시퀀스, 상태머신, 스윔레인, 폴더트리, 2단 비교를 그릴 때 **해당 패턴 섹션을 반드시 읽고 규격대로** 그린다. 즉흥적 박스 나열로 대체하지 말 것. |
| `references/icons.md` | 카드 헤더나 배지에 도메인 아이콘(MCU, CAN, 모터, DB 등)을 넣을 때 path를 복사해 쓴다. 아이콘을 즉석에서 새로 그리지 말 것. |

## 핵심 규칙

### 1. 루트 `<svg>` 속성

루트 `<svg>` 태그에는 **`viewBox`만** 지정한다. **`width="100%"`는 절대 쓰지 않는다.**

- `width`, `height` 속성 자체를 생략한다.
- **표준 viewBox 폭: 720px** (Confluence 첨부, 일반 다이어그램 기본값). 좁은 도식은 400~600, 넓은 시퀀스/스윔레인은 900~1000 허용.
- 실제 표시 크기는 SVG를 감싸는 컨테이너가 결정하도록 둔다.

**이유**: `width="100%"`는 부모 요소가 명시적 폭을 갖지 않을 때 0px로 계산되어 SVG가 사라지거나 의도보다 크게 늘어난다. `viewBox`만 지정하면 컨테이너 크기에 비례해 늘어나며 종횡비도 유지된다.

### 2. font-family

SVG 안의 모든 텍스트에 다음 스택을 `<style>` 블록에서 일괄 적용한다:

```
"현대하모니 M", "HDharmony M", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

현대하모니는 웨이트가 별도 family(`현대하모니 L/M/B`)로 나뉘므로 본문은 `현대하모니 M`, 굵게는 `현대하모니 B`를 지정한다(font-weight로는 굵기 전환 안 됨). 미설치 환경에서는 Pretendard → 시스템 한글 폰트로 자동 폴백된다.

### 3. 폰트 크기 및 두께 (viewBox 폭 720 기준)

| 클래스 | 용도 | 크기 | 두께 |
| --- | --- | --- | --- |
| `.h1` | 다이어그램 제목 | 20~22px | 600 |
| `.col-head` | 컬럼 헤더 | 15px | 600 |
| `.card-title` | 카드 타이틀 | 18~21px | 500~600 |
| `.band-title` | 헤더 밴드 타이틀 (§11) | 15px | 500 |
| `.sub` | 부제목 (회색) | 14px | 400 |
| `.sec` | 섹션 헤더 텍스트 | 15px | 500 |
| `.zone-lbl` | 그룹 존 라벨 (§11) | 13px | 500 |
| `.lbl` | 라벨 | 14~16px | 500 |
| `.body` | 본문 | 14~16px | 400 |
| `.caption` | 캡션 | 13px | 400 |
| `.cap` | 작은 캡션 | 12px | 400 |
| `.chip-txt` | 칩/배지 텍스트 (§11) | 12px | 500 |
| `.micro` | 매우 작은 보조 텍스트 | 10~11px | 400 |

**원칙**: 기본 두께 400/500, 시각 anchor(카드 타이틀·컬럼 헤더)만 600 허용. 정보 밀도가 높을 때(한 박스 4줄 이상, 셀 많은 표, viewBox 폭 400~500)만 한 단계 축소 허용하되 **본문은 12px 미만 금지**.

### 4. viewBox 폭 대비 폰트 비율

같은 폰트 크기여도 viewBox 폭이 다르면 렌더링 크기가 달라진다. 720이 아닌 폭을 쓸 때는 비율 유지:

| 항목 | viewBox 폭 대비 비율 |
| --- | --- |
| 제목 (h1) | 2.8 ~ 3.0 % |
| 카드 타이틀 | 2.5 ~ 2.9 % |
| 본문 (body) | 2.0 ~ 2.3 % |
| 캡션 | 1.7 ~ 1.9 % |
| 박스 내부 좌측 여백 | 20px 고정 |
| 박스 폭 (2단 레이아웃) | 45 ~ 48 % |

**검증**: `body 폰트 / viewBox 폭 × 100` ≈ 2%. 예: 720→16px(2.2%), 1000→22px, 480→11px.

### 5. 색상 팔레트 (5톤 파스텔 + 중립 회색, 확장 틴트 포함)

| 톤 | 의미 | 박스 fill | 밴드 fill (mid) | 존 틴트 | stroke | 텍스트 진한 | 텍스트 연한 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Beige | 입력 · MCAL · 원본 | rgb(250,238,218) | rgb(221,198,166) | rgb(253,247,237) | rgb(133,79,11) | rgb(99,56,6) | rgb(133,79,11) |
| Blue | 처리 · BSW · 도구 | rgb(230,241,251) | rgb(179,205,230) | rgb(243,248,253) | rgb(24,95,165) | rgb(12,68,124) | rgb(24,95,165) |
| Mint | 결과 · 정본 · 핵심 | rgb(225,245,238) | rgb(173,211,200) | rgb(240,250,247) | rgb(15,110,86) | rgb(8,80,65) | rgb(15,110,86) |
| Lavender | 파생물 · 산출물 | rgb(238,237,254) | rgb(199,196,236) | rgb(247,246,255) | rgb(83,74,183) | rgb(60,52,137) | rgb(83,74,183) |
| Coral | 경고 · 비용 · 위험 | rgb(250,236,231) | rgb(226,192,181) | rgb(253,246,243) | rgb(153,60,29) | rgb(113,43,19) | rgb(153,60,29) |
| Grey | 중립 · 비활성 | rgb(247,246,244) | rgb(230,229,226) | rgb(251,251,250) | rgb(180,178,170) | rgb(115,114,108) | rgb(140,138,130) |

- **박스 fill** = 일반 카드 배경. **밴드 fill** = 헤더 밴드·강조 배경(파스텔보다 한 단계 진함). **존 틴트** = 그룹 존 배경(파스텔보다 한 단계 연함). 세 단계 명도로 깊이를 만든다.
- **stroke 색은 fill로도 쓸 수 있다** — 액센트 바, 번호 배지, 스트롱 밴드(§11) 한정. 이때 위 텍스트는 흰색 `rgb(255,255,255)` 또는 해당 톤 박스 fill 색.
- 팔레트 밖의 임의 진한 채도(`#1e3a8a`, `#f59e0b` 등)는 직접 쓰지 않는다.
- **톤 배정 원칙**: 색은 의미(역할·카테고리)를 담는다. 순서대로 무지개처럼 돌려쓰지 말 것. 한 다이어그램에 유채색 톤 **3개 이하** + grey.

### 6. 테두리·모서리·대비 등급

- 기본 `stroke-width`: **0.5** (일반 박스, 존, 칩)
- **0.75**: viewBox 폭 900 이상이거나 문서에서 축소 게재가 예상되는 넓은 다이어그램의 박스
- **1.0**: hero 박스(§11) 전용
- 모서리 `rx`: 작은 셀 4 / 섹션 헤더 밴드 6 / 주요 박스·카드 8~10 / 그룹 존 12 / 칩 높이의 절반(pill)
- 그림자·filter(feDropShadow 등)는 사용하지 않는다 — Confluence 이미지 변환에서 렌더링을 보장할 수 없다. 깊이는 존 틴트·밴드·액센트 바의 명도 3단계로 만든다.

### 7. 박스 높이와 상하 여백 (반드시 동일하게)

박스 높이는 텍스트 줄 수에 비례, **상단·하단 시각적 여백은 12~13px로 동일**해야 한다. 시각적 여백은 baseline이 아니라 텍스트의 실제 시각적 가장자리(cap height 상단 / descender 하단) 기준이다.

**baseline 보정값** (시각적 상단 = baseline − 보정값 / 시각적 하단 = baseline + 3):

| 폰트 크기 | 상단 보정 | 하단 보정 |
| --- | --- | --- |
| 17~18px (card-title) | 13px | 4px |
| 15px (band-title) | 11px | 3px |
| 13~14px (body/caption) | 10px | 3px |

**계산식**:
- 첫 줄이 card-title(17px): `첫 baseline = 박스 상단 + 26`
- 첫 줄이 body(14px): `첫 baseline = 박스 상단 + 23`
- 마지막 줄 뒤: `박스 하단 = 마지막 baseline + 15`
- 줄 간격: 18~20px (baseline 간), card-title→body는 23px

**검증 (필수)**: 박스마다
```
상단 여백 = 첫 baseline − 상단 보정값 − 박스 상단 y
하단 여백 = 박스 하단 y − 마지막 baseline − 3
```
두 값 모두 12~13px, 차이 2px 이하.

**예시** — 본문 4줄(14px): 상단 y=100 → baseline 123/141/159/177 → 하단 192 (높이 92). 상단 여백 13 ✓ / 하단 여백 12 ✓.

### 8. 요소 간 간격

- **같은 섹션 내 박스 간 세로 간격: 12~16px** (기본 14). 모든 간격이 ±2px 범위로 일관.
- **섹션 타이틀과 이전 박스 사이: 시각적 간격 30~40px** (기본 35 → 타이틀 baseline = 이전 박스 하단 + 48). 박스 간 간격보다 명확히 커야 섹션 분리감이 생긴다.
- **섹션 타이틀과 아래 첫 박스 사이: 시각적 간격 14~20px** (기본 18 → 박스 상단 = 타이틀 baseline + 21).
- 안티 패턴: 간격 들쭉날쭉(한 박스만 동떨어져 보임), 섹션 간격 ≤ 박스 간격(분리감 없음), 타이틀이 박스에 밀착(박스 일부처럼 보임).

### 9. 커넥터 3종 체계

`<defs>` marker 하나로 모든 화살표 머리를 공유한다 (`context-stroke`라 선 색을 자동 상속):

```svg
<defs>
  <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
</defs>
```

| 종류 | 용도 | 스타일 |
| --- | --- | --- |
| 주 흐름 (실선) | 기본 연결, 동기 호출 | stroke `rgb(140,138,130)` / width 1.5 |
| 보조 흐름 (점선) | 비동기, 선택적, 피드백, 참조 | 같은 색 / width 1.2 / `stroke-dasharray="6 4"` |
| 핵심 경로 (톤 실선) | 다이어그램의 주인공 경로 강조 — **다이어그램당 1개 경로만** | 해당 톤 stroke 색 / width 2 |

- **길이**: 라벨 없는 화살표 30~40px 적정, 100px 이상이면 박스 간격을 줄인다.
- **라벨 있는 가로 화살표**: `화살표 길이 ≈ 라벨 폭 + 20` (양옆 여유 10px씩). 라벨 폭 추정: 영문 1자 7~8px, 한글 13px (caption 13px 기준). 이 규칙이 30~40px 가이드보다 우선한다.
- **직교 라우팅**: 직선 경로가 다른 박스나 텍스트를 관통하면 L자 우회 — `<path d="M x1 y1 V ym H x2 V y2" fill="none"/>`. 커넥터 path에는 **반드시 `fill="none"`** (없으면 검은 면으로 렌더링).
- **양방향**: `marker-start`와 `marker-end`를 모두 지정.

### 10. 접근성 태그 (필수)

```svg
<svg viewBox="..." role="img">
  <title>다이어그램의 한 줄 요약 제목</title>
  <desc>다이어그램이 무엇을 설명하는지 한두 문장</desc>
</svg>
```

## 11. 표현 장치 (밋밋함 방지 — 규격대로만 사용)

콘텐츠가 같아도 아래 장치의 유무가 다이어그램의 완성도를 좌우한다. 단, §12 가드레일 안에서만 쓴다.

### 11-1. 좌측 액센트 바

카드의 좌측 가장자리에 톤 stroke 색의 세로 바를 붙여 역할·중요도를 표시한다.

```svg
<rect x="{박스x}" y="{박스y+3}" width="4" height="{박스높이-6}" rx="2" fill="{톤 stroke 색}"/>
```

상하 3px 인셋 + rx 2로 박스의 둥근 모서리와 충돌하지 않는다. 박스 rect **뒤에**(위에) 그린다. 액센트 바가 있는 카드의 텍스트 좌측 여백은 20 → **24px**.

### 11-2. 카드 헤더 밴드

카드 상단에 타이틀 전용 배경 밴드를 깐다. 밴드 높이 **32px**, 타이틀은 `.band-title`(15px/500), baseline = 밴드 상단 + 21. 밴드 아래 첫 body baseline = 밴드 하단 + 23.

윗모서리만 둥근 밴드 path (r = 박스 rx):

```svg
<path d="M {bx} {by+r} q0 {-r} {r} {-r} h {w-2r} q {r} 0 {r} {r} v {32-r} h {-w} z" fill="{밴드 색}"/>
```

- **밴드-라이트 (기본)**: fill = 톤 **밴드 fill(mid)**, 타이틀 = 톤 진한 텍스트 색.
- **밴드-스트롱 (hero 전용)**: fill = 톤 **stroke 색**, 타이틀 = 톤 **박스 fill 색**(밝은 파스텔) 또는 흰색.

### 11-3. 그룹 존

관련 카드들을 하나의 영역으로 묶는 배경 컨테이너. 관계 표현을 화살표에만 의존하지 않게 한다.

```svg
<rect x=".." y=".." width=".." height=".." rx="12"
      fill="{톤 존 틴트}" stroke="{톤 stroke}" stroke-width="0.5" stroke-dasharray="4 3"/>
<text x="{존x+16}" y="{존y+24}" class="zone-lbl" fill="{톤 연한 텍스트}">존 라벨</text>
```

- 존 라벨 영역: 상단 40px (라벨 baseline = 존 상단 + 24, 내부 첫 카드 상단 = 존 상단 + 40)
- 내부 패딩: 좌우·하단 16px
- 존 안의 카드는 존과 **다른 톤**이거나 같은 톤의 박스 fill(틴트보다 진해서 자연히 구분됨)
- 존 중첩은 1단까지만

### 11-4. 스텝 번호 배지

순서가 있는 플로우의 각 카드에 번호를 단다.

```svg
<circle cx="{cx}" cy="{cy}" r="11" fill="{톤 stroke 색}"/>
<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central"
      class="chip-txt" fill="rgb(255,255,255)">1</text>
```

위치: 카드 내부 좌상단(카드 타이틀 왼쪽, cx = 박스x + 24, cy = 타이틀 baseline − 5) 또는 카드 좌상단 모서리 걸침(cx = 박스x, cy = 박스y — 이때 배지가 잘리지 않게 viewBox 여백 확인).

### 11-5. 상태 칩

핵심/주의/진행/비활성 같은 상태를 pill로 표시한다. 높이 **20px**, rx **10**, 텍스트 12px/500, 좌우 패딩 10px (칩 폭 = 텍스트 폭 + 20).

```svg
<rect x=".." y=".." width="{텍스트폭+20}" height="20" rx="10"
      fill="{톤 박스 fill}" stroke="{톤 stroke}" stroke-width="0.5"/>
<text x="{칩 중앙}" y="{칩y+10}" text-anchor="middle" dominant-baseline="central"
      class="chip-txt" fill="{톤 진한 텍스트}">핵심</text>
```

권장 의미: mint=핵심/완료, blue=진행, coral=주의/위험, grey=비활성/예정. 위치: 카드 우상단(우측 여백 12px) 또는 타이틀 오른쪽.

### 11-6. hero 박스 (다이어그램당 최대 1개)

다이어그램의 주인공 하나만 격상한다: `stroke-width: 1` + 밴드-스트롱 또는 액센트 바. 모든 박스가 hero면 아무것도 hero가 아니다.

### 11-7. 도메인 아이콘

카드 헤더·배지에 의미를 즉시 전달하는 아이콘(MCU, CAN 버스, 모터, DB, 경고 등)을 넣을 수 있다. **`references/icons.md`의 path를 그대로 복사**해 쓴다(즉석 창작 금지). 규격: 18×18 그리드, stroke 스타일(fill none, stroke-width 1.2, round cap/join), 색은 톤 stroke 또는 진한 텍스트 색. 배치는 `<g transform="translate(x,y)">`.

## 12. 과잉 방지 가드레일

표현 장치는 강력하지만 남용하면 장식 과다로 넘어간다. 다음 상한을 지킨다:

- 한 다이어그램에 표현 장치(액센트 바 / 헤더 밴드 / 그룹 존 / 번호 배지 / 상태 칩 / 아이콘) **종류 3개 이하**
- hero 박스 **최대 1개**, 핵심 경로(톤 화살표) **최대 1개** — 이 둘은 위 3종 카운트와 별개로 허용 (강조 대상은 항상 존재할 수 있어야 하므로)
- 아이콘은 의미가 있을 때만, **다이어그램당 6개 이하**
- 유채색 톤 3개 이하 + grey (§5)
- 단순한 2~4박스 도식에는 장치 없이 기본 카드만 써도 된다 — 장치는 밀도가 있는 다이어그램의 위계를 만들 때 쓰는 것

## 13. 텍스트 오버플로 검사 (출력 전 필수 — 예외 없음)

SVG의 `<text>`는 자동 줄바꿈이 없다. 박스보다 긴 텍스트는 **그대로 박스를 뚫고 나가며**, 이것이 가장 흔하고 가장 눈에 띄는 실패다. 모든 SVG는 출력 직전에 아래 검사를 반드시 통과해야 한다.

### 텍스트 폭 추정표 (문자당 폭 = 계수 × 폰트 크기)

| 문자 종류 | 계수 |
| --- | --- |
| 한글 | **1.0** |
| 영문 대문자 | 0.7 |
| 영문 소문자 · 숫자 | **0.6** |
| 공백 · 쉼표 · 마침표 · 괄호 | 0.4 |
| 중점(·) · 하이픈 | 0.5 |
| 대시(—) · 화살표(→) | 1.0 |

빠른 계산: `추정 폭 ≈ (한글 자수 × 크기) + (영문·숫자 자수 × 0.6 × 크기) + (기호·공백 자수 × 0.45 × 크기)`

예: 12px 캡션 `can.interfaces.<name> · 지연(lazy) 로드` → 영문 25자×7.2=180 + 한글 4자×12=48 + 기호 6자×5.4=32 ≈ **260px**

### 사전 규칙: 박스 폭은 텍스트가 정한다

박스를 먼저 그리고 텍스트를 욱여넣지 말 것. 박스 `<rect>`를 쓰기 전에 그 안에 들어갈 **가장 긴 줄의 추정 폭**을 계산하고, `박스 폭 ≥ 최장 줄 추정 폭 + 32` (좌 20 + 우 12)를 확보한다. 레이아웃상 박스 폭이 고정이라면 텍스트를 그 폭에 맞춰 먼저 다듬는다.

### 검사 절차 (박스 안의 모든 텍스트 줄에 대해)

```
사용 가능 폭 = 박스 우측 x − 텍스트 시작 x − 우측 여백 12
추정 폭 ≤ 사용 가능 폭  →  통과
```

- `text-anchor="middle"`이면: 추정 폭 ≤ 박스 폭 − 좌우 여백 24
- `text-anchor="end"`이면: 텍스트 x − 추정 폭 ≥ 박스 좌측 x + 12
- 화살표 라벨·존 라벨·범례 등 박스 밖 텍스트는 viewBox 경계(0 ~ viewBox 폭)와 인접 박스 침범 여부를 검사

### 검사 실패 시 대응 (우선순위 순)

1. **텍스트 축약** — 조사·수식어 제거, 영문 축약 (`인터페이스 백엔드 로드` → `백엔드 로드`, `(lazy)` 삭제)
2. **2줄 분리** — 박스 높이를 §7 계산식으로 재산정하고 아래 요소들을 함께 내림
3. **박스 폭 확대** — 레이아웃이 허용하면 (§4 박스 폭 비율 범위 내에서)
4. **폰트 한 단계 축소** — 최후 수단, 본문 12px 미만 금지 유지

**절대 금지**: 넘치는 것을 알면서 그대로 출력하는 것. "대충 맞겠지"로 넘어가지 말고 긴 줄(대략 사용 가능 폭의 70% 이상으로 보이는 줄)은 전부 계산한다.

## 표준 템플릿

```svg
<svg viewBox="0 0 720 540" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>다이어그램 제목</title>
  <desc>이 다이어그램이 설명하는 내용 한두 문장</desc>

  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>

  <style>
    text { font-family: "현대하모니 M", "HDharmony M", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: rgb(20, 20, 19); }
    .h1 { font-size: 21px; font-weight: 600; }
    .col-head { font-size: 15px; font-weight: 600; fill: rgb(115, 114, 108); }
    .sub { font-size: 14px; font-weight: 400; fill: rgb(115, 114, 108); }
    .sec { font-size: 15px; font-weight: 500; }
    .card-title { font-size: 18px; font-weight: 500; }
    .band-title { font-size: 15px; font-weight: 500; }
    .zone-lbl { font-size: 13px; font-weight: 500; }
    .lbl { font-size: 14px; font-weight: 500; }
    .body { font-size: 14px; font-weight: 400; }
    .caption { font-size: 13px; font-weight: 400; fill: rgb(140, 138, 130); }
    .cap { font-size: 12px; font-weight: 400; }
    .chip-txt { font-size: 12px; font-weight: 500; }
    .micro { font-size: 10px; font-weight: 400; }
    rect.box { stroke-width: 0.5; }

    /* 박스 색상 (fill/stroke) */
    .beige { fill: rgb(250, 238, 218); stroke: rgb(133, 79, 11); }
    .blue { fill: rgb(230, 241, 251); stroke: rgb(24, 95, 165); }
    .mint { fill: rgb(225, 245, 238); stroke: rgb(15, 110, 86); }
    .lav { fill: rgb(238, 237, 254); stroke: rgb(83, 74, 183); }
    .coral { fill: rgb(250, 236, 231); stroke: rgb(153, 60, 29); }
    .grey { fill: rgb(247, 246, 244); stroke: rgb(180, 178, 170); }

    /* 존 틴트 (그룹 존 배경) */
    .z-beige { fill: rgb(253, 247, 237); stroke: rgb(133, 79, 11); }
    .z-blue { fill: rgb(243, 248, 253); stroke: rgb(24, 95, 165); }
    .z-mint { fill: rgb(240, 250, 247); stroke: rgb(15, 110, 86); }
    .z-lav { fill: rgb(247, 246, 255); stroke: rgb(83, 74, 183); }
    .z-coral { fill: rgb(253, 246, 243); stroke: rgb(153, 60, 29); }
    .z-grey { fill: rgb(251, 251, 250); stroke: rgb(180, 178, 170); }

    /* 텍스트 색상 (각 톤의 진한/연한 페어) */
    .t-beige-d { fill: rgb(99, 56, 6); } .t-beige-l { fill: rgb(133, 79, 11); }
    .t-blue-d { fill: rgb(12, 68, 124); } .t-blue-l { fill: rgb(24, 95, 165); }
    .t-mint-d { fill: rgb(8, 80, 65); } .t-mint-l { fill: rgb(15, 110, 86); }
    .t-lav-d { fill: rgb(60, 52, 137); } .t-lav-l { fill: rgb(83, 74, 183); }
    .t-coral-d { fill: rgb(113, 43, 19); } .t-coral-l { fill: rgb(153, 60, 29); }
    .t-grey-l { fill: rgb(115, 114, 108); } .t-grey-ll { fill: rgb(140, 138, 130); }
    .t-white { fill: rgb(255, 255, 255); }

    line.arr, path.arr { fill: none; stroke: rgb(140, 138, 130); stroke-width: 1.5; }
    line.arr-sub, path.arr-sub { fill: none; stroke: rgb(140, 138, 130); stroke-width: 1.2; stroke-dasharray: 6 4; }
    .zone { stroke-width: 0.5; stroke-dasharray: 4 3; }
  </style>

  <!-- 콘텐츠 -->
</svg>
```

### 표현 장치 조합 예시 (그룹 존 + 액센트 바 + 번호 배지 + 상태 칩)

```svg
<!-- 그룹 존 -->
<rect x="20" y="60" width="330" height="270" rx="12" class="z-blue zone"/>
<text x="36" y="84" class="zone-lbl t-blue-l">통신 서비스 존</text>

<!-- 카드 1: 액센트 바 + 번호 배지 -->
<rect x="36" y="100" width="298" height="92" rx="8" class="blue box"/>
<rect x="36" y="103" width="4" height="86" rx="2" fill="rgb(24,95,165)"/>
<circle cx="60" cy="121" r="11" fill="rgb(24,95,165)"/>
<text x="60" y="121" text-anchor="middle" dominant-baseline="central" class="chip-txt t-white">1</text>
<text x="80" y="126" class="card-title t-blue-d" style="font-size:17px">Com 모듈</text>
<text x="60" y="152" class="body t-blue-l">시그널 라우팅 처리</text>
<text x="60" y="172" class="body t-blue-l">PDU 송수신 관리</text>

<!-- 카드 2: hero (stroke 1 + 상태 칩) -->
<rect x="36" y="206" width="298" height="92" rx="8" class="mint" style="stroke-width:1"/>
<circle cx="60" cy="227" r="11" fill="rgb(15,110,86)"/>
<text x="60" y="227" text-anchor="middle" dominant-baseline="central" class="chip-txt t-white">2</text>
<text x="80" y="232" class="card-title t-mint-d" style="font-size:17px">CanIf 모듈</text>
<rect x="270" y="216" width="52" height="20" rx="10" class="mint box"/>
<text x="296" y="226" text-anchor="middle" dominant-baseline="central" class="chip-txt t-mint-d">핵심</text>
<text x="60" y="258" class="body t-mint-l">하드웨어 추상화</text>
<text x="60" y="278" class="body t-mint-l">컨트롤러 상태 관리</text>

<line x1="185" y1="192" x2="185" y2="204" class="arr" marker-end="url(#arr)"/>
```

## 안티 패턴 (하지 말 것)

```svg
<!-- ❌ width="100%" (컨테이너에 따라 0px로 사라짐) -->
<svg width="100%" height="100%" viewBox="0 0 800 600">...</svg>

<!-- ❌ viewBox 폭 대비 폰트 과소 (11/1200 = 0.9%) -->
<svg viewBox="0 0 1200 800"><text font-size="11">...</text></svg>

<!-- ❌ 본문 12px 미만 (가독성 급락) -->
<text font-size="9" class="body">중요한 본문</text>

<!-- ❌ 박스가 줄 수 대비 과대 (본문 1줄에 높이 200px → 80px가 적정) -->

<!-- ❌ 상하 여백 불일치 (상단 13px / 하단 2px → §7 검증식으로 계산해 맞출 것) -->

<!-- ❌ baseline 기준으로만 여백 측정 (폰트 크기 다르면 시각적 여백 어긋남 → §7 보정값 사용) -->

<!-- ❌ 굵은 테두리 (stroke-width 2 이상. hero도 1까지만) -->
<rect stroke-width="2" .../>

<!-- ❌ 팔레트 밖 진한 채도 직접 사용 -->
<rect fill="#1e3a8a"/>

<!-- ❌ feDropShadow 등 filter 사용 (Confluence 렌더링 미보장) -->
<rect filter="url(#shadow)" .../>

<!-- ❌ 모든 박스에 밴드+배지+칩+액센트 바 도배 (§12 가드레일 위반, hero 실종) -->

<!-- ❌ 커넥터 path에 fill 미지정 (검은 면으로 렌더링됨) -->
<path d="M100 100 V150 H300" marker-end="url(#arr)"/>

<!-- ❌ title/desc 없음, font-family 누락 -->

<!-- ❌ 화살표가 너무 김 (150px → 박스 간격을 좁혀 30~40px로) -->

<!-- ❌ 텍스트가 박스를 벗어남 (§13 미검사) -->
<rect x="180" y="478" width="360" .../>  <!-- 우측 끝 540 -->
<text x="200" class="cap">can.interfaces.&lt;name&gt; · 지연(lazy) 로드 — 잘못된 이름은 여기서 실패</text>
<!-- 추정 폭 ≈ 400px, 시작 200 → 끝 600 > 540. 축약하거나 2줄로 분리해야 함 -->
```

## 체크리스트

SVG를 출력하기 전 다음을 모두 확인한다:

- [ ] 루트 `<svg>`에 `viewBox`가 있고 `width="100%"`가 **없다**.
- [ ] viewBox 폭은 **720 기본** (좁은 도식 400~600, 넓은 시퀀스/스윔레인 900~1000).
- [ ] `role="img"`, `<title>`, `<desc>` 3종 세트가 있다.
- [ ] `<style>` 블록에 폰트 스택과 색상 클래스가 정의되어 있고 첫 폰트는 `"현대하모니 M"`.
- [ ] **본문 폰트 / viewBox 폭 ≈ 2.0~2.3%**, 본문 12px 미만 없음.
- [ ] 박스 상하 시각적 여백 12~13px, 차이 2px 이하 (§7 검증식으로 계산했다).
- [ ] **[필수] 모든 박스 내 텍스트에 §13 오버플로 검사를 수행했다** — 긴 줄은 추정표로 계산해 `추정 폭 ≤ 사용 가능 폭`을 확인했고, 실패한 줄은 축약/2줄 분리/폭 확대로 해결했다. 이 항목을 건너뛴 SVG는 출력 금지.
- [ ] 같은 섹션 내 박스 간격 12~16px 일관, 섹션 분리 30~40px (§8).
- [ ] 색은 팔레트(박스 fill / 밴드 fill / 존 틴트 / stroke)의 정확한 RGB만 사용, 유채색 3톤 이하.
- [ ] stroke-width는 0.5 기본 / 넓은 다이어그램 0.75 / hero 1 — 이 셋뿐이다.
- [ ] 커넥터는 3종 체계(실선/점선/핵심 경로) 중 하나이고, path 커넥터에 `fill="none"`이 있다.
- [ ] 화살표 길이 적정 (라벨 있으면 라벨 폭 + 20 우선), 다른 박스 관통 시 L자 우회했다.
- [ ] **표현 장치(바/밴드/존/배지/칩/아이콘) 종류 3개 이하 + hero 최대 1개 + 핵심 경로 최대 1개, 아이콘 6개 이하** (§12).
- [ ] 액센트 바/밴드/존/배지/칩을 썼다면 §11의 수치 규격 그대로다.
- [ ] **레이어 스택·파이프라인·시퀀스·상태머신·스윔레인·폴더트리·2단 비교를 그렸다면 `references/patterns.md`의 해당 규격을 읽고 그대로 따랐다.**
- [ ] 아이콘을 썼다면 `references/icons.md`의 path를 복사했다 (즉석 창작 아님).

## 적용 범위

- 독립 `.svg` 파일 생성
- HTML 문서 안의 인라인 `<svg>` 마크업
- React/JSX 컴포넌트 안의 `<svg>` 엘리먼트
- Confluence 페이지 첨부용 SVG (`confluence-writing` 스킬과 함께)
- 포트폴리오/문서 삽입용 다이어그램 (`portfolio-theme` 스킬과 함께)
- `visualize:show_widget` SVG 모드

다른 SVG 관련 디자인 규칙이 다른 스킬에 정의되어 있다면 병행 적용한다.
