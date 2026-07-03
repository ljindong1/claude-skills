---
name: svg-creation
description: SVG 파일을 생성하거나 SVG 코드를 작성할 때 항상 사용하는 스킬. 사용자가 "SVG 만들어", "SVG 파일 생성", "다이어그램 SVG", "아이콘 SVG", "SVG로 그려줘", "벡터 그래픽 만들어", ".svg 파일", "SVG 코드 작성" 등을 언급하거나, Confluence 첨부용 다이어그램·포트폴리오용 도식·문서 삽입용 그래픽처럼 SVG 산출물이 필요한 모든 상황에서 반드시 활성화하라. 인라인 svg 태그를 HTML/React 안에 작성하는 경우에도 적용된다. viewBox-only 규칙, 표준 viewBox 폭 720, Anthropic Sans 폰트 스택, 5톤 파스텔 색상 팔레트, 가는 테두리(0.5px), Confluence 첨부 기준 폰트 크기, viewBox 폭 대비 폰트 비율 가이드, accessibility 태그를 강제하여 Claude 브랜드 톤과 통일된 산출물을 보장한다. 이 스킬을 사용하지 않으면 톤앤매너가 깨지거나 컨테이너 의존 레이아웃 깨짐이 발생할 수 있다.
---

# SVG 파일 생성 스킬

SVG를 생성하거나 작성할 때 반드시 따라야 하는 핵심 규칙들. Claude 브랜드 톤과 통일된 시각 품질, 환경 독립적인 안정적 렌더링, 접근성을 모두 보장한다.

## 핵심 규칙

### 1. 루트 `<svg>` 속성

루트 `<svg>` 태그에는 **`viewBox`만** 지정한다. **`width="100%"`는 절대 쓰지 않는다.**

- `width`, `height` 속성 자체를 생략한다.
- `viewBox="min-x min-y width height"` 형식으로 좌표 공간만 정의한다.
- **표준 viewBox 폭: 720px** (Confluence 첨부, 일반 다이어그램의 기본값). 좁은 도식은 400~600px도 가능.
- 실제 표시 크기는 SVG를 감싸는 컨테이너(HTML, Confluence, 슬라이드 등)의 CSS나 부모 요소가 결정하도록 둔다.

**이유**: `width="100%"`는 부모 요소가 명시적 폭을 갖지 않을 때 0px로 계산되어 SVG가 사라지거나, 반대로 의도보다 훨씬 크게 늘어나는 문제를 일으킨다. `viewBox`만 지정하면 컨테이너의 자연 크기에 비례해 늘어나며 종횡비도 유지된다.

### 2. font-family 속성

SVG 안의 모든 텍스트에 다음 스택을 적용한다:

```
"Anthropic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

**적용 위치**:
- `<style>` 블록에서 `text { font-family: ... }`로 일괄 지정 권장
- 한글 텍스트는 시스템 한글 폰트로 자동 폴백 (Windows: Malgun Gothic, macOS: Apple SD Gothic Neo)

**이유**: Anthropic Sans는 Claude 브랜드 폰트로 영문·숫자 가독성과 톤이 우수하다. 한글은 시스템 한글 폰트로 폴백되어 환경별로 자연스럽게 표시된다.

### 3. 폰트 크기 및 두께 (Confluence 첨부 기준)

**viewBox 폭 720px 기준 표준 크기**. Confluence, 문서 본문(폭 760~960px)으로 렌더링될 때 가독성이 확보되는 값이다.

| 클래스 | 용도 | 크기 | 두께 |
| --- | --- | --- | --- |
| `.h1` | 다이어그램 제목 | 20~22px | 600 (semi-bold) |
| `.col-head` | 컬럼 헤더 (좌/우 그룹 구분) | 15px | 600 |
| `.card-title` | 카드 타이틀 | 18~21px | 500~600 |
| `.sub` | 부제목 (회색) | 14px | 400 |
| `.sec` | 섹션 헤더 밴드 텍스트 | 15px | 500 |
| `.lbl` | 라벨 | 14~16px | 500 |
| `.body` | 본문 | 14~16px | 400 |
| `.caption` | 캡션 | 13px | 400 |
| `.cap` | 작은 캡션 | 12px | 400 |
| `.micro` | 매우 작은 보조 텍스트 | 10~11px | 400 |

**원칙**: 기본 두께는 400 또는 500. 카드 타이틀과 컬럼 헤더처럼 시각적 anchor가 필요한 곳은 600 허용.

#### 예외: 정보 밀도가 높을 때만 축소

위 표는 **충분한 공간이 있을 때의 표준값**이다. 다음 경우에 한해 한 단계씩 축소 허용:

- 한 박스에 4줄 이상의 본문이 들어가야 하는 경우
- 표(테이블) 형태로 셀이 많아 좁은 셀 폭에 텍스트를 넣어야 하는 경우
- viewBox 폭을 720보다 좁게(예: 400~500) 잡아야 하는 경우

축소할 때도 본문은 **12px 이하로 내려가지 않게 한다**. 12px 미만은 Confluence/문서 렌더링에서 가독성이 급격히 떨어진다.

### 4. viewBox 폭 대비 폰트 비율 가이드

**같은 폰트 크기여도 viewBox 폭이 다르면 렌더링 크기가 달라진다.** viewBox 폭은 픽셀이 아니라 "단위"이기 때문이다. 컨테이너에 SVG가 fit되면서 viewBox 폭이 클수록 폰트가 상대적으로 작아 보인다.

viewBox 폭 720을 기본으로 잡되, 다른 폭을 쓸 때는 다음 비율을 유지한다:

| 항목 | viewBox 폭 대비 비율 |
| --- | --- |
| 다이어그램 제목 (h1) | 2.8 ~ 3.0 % |
| 카드 타이틀 | 2.5 ~ 2.9 % |
| 본문 (body) | 2.0 ~ 2.3 % |
| 캡션 | 1.7 ~ 1.9 % |
| 박스 내부 좌측 여백 (padding-left) | 20px 고정 (viewBox와 무관) |
| 박스 폭 (2단 레이아웃의 한 박스) | 45 ~ 48 % |

**검증 방법**: SVG를 다 그린 뒤 `body 폰트 크기 / viewBox 폭 × 100` 을 계산해 2% 근처인지 확인한다.

예시:
- viewBox 폭 720 → body 16px (16/720 = 2.2% ✓)
- viewBox 폭 1000 → body 22px이 적정 (22/1000 = 2.2%). 16px이면 1.6%로 작아 보인다.
- viewBox 폭 480 → body 11~12px이 적정 (11/480 = 2.3%).

### 5. 색상 팔레트 (5톤 파스텔 + 중립 회색)

| 톤 | 의미 (권장 용도) | 박스 fill | 박스 stroke | 텍스트 진한 | 텍스트 연한 |
| --- | --- | --- | --- | --- | --- |
| Beige | 입력 · MCAL · 원본 | rgb(250, 238, 218) | rgb(133, 79, 11) | rgb(99, 56, 6) | rgb(133, 79, 11) |
| Blue | 처리 · BSW · 도구 | rgb(230, 241, 251) | rgb(24, 95, 165) | rgb(12, 68, 124) | rgb(24, 95, 165) |
| Mint | 결과 · 정본 · 핵심 | rgb(225, 245, 238) | rgb(15, 110, 86) | rgb(8, 80, 65) | rgb(15, 110, 86) |
| Lavender | 파생물 · 산출물 | rgb(238, 237, 254) | rgb(83, 74, 183) | rgb(60, 52, 137) | rgb(83, 74, 183) |
| Coral | 경고 · 비용 · 위험 | rgb(250, 236, 231) | rgb(153, 60, 29) | rgb(113, 43, 19) | rgb(153, 60, 29) |
| Grey | 중립 · 비활성 | rgb(247, 246, 244) | rgb(180, 178, 170) | rgb(115, 114, 108) | rgb(140, 138, 130) |

**원칙**: 진한 채도(`#1e3a8a`, `#f59e0b` 등)는 직접 쓰지 않는다. 위 RGB 값만 사용.

### 6. 테두리 및 모서리

- 모든 박스의 `stroke-width`: **0.5** (가는 테두리)
- 모서리 반경 `rx`:
  - 작은 셀 (테이블 행 등): **4px**
  - 섹션 헤더 밴드: **6px**
  - 주요 박스 / 카드: **8~10px**

### 7. 박스 높이와 상하 여백 (반드시 상하 동일하게)

박스 높이는 내부 텍스트 줄 수에 비례해서 잡고, **상단 여백과 하단 여백은 반드시 동일**해야 한다. 한쪽이 더 넓으면 텍스트가 위 또는 아래로 쏠려 보여 시인성이 떨어진다.

#### 표준 상하 여백: 12~13px (시각적 여백 기준)

**시각적 여백**이란 텍스트의 baseline이 아니라 텍스트의 실제 시각적 가장자리(cap height 상단, descender 포함 하단)와 박스 경계 사이의 거리다. baseline 기준으로 측정하면 폰트 크기가 다른 텍스트끼리 여백이 어긋난다.

**폰트 크기별 baseline 위치 보정값** (텍스트 시각적 상단 = baseline - 보정값):

| 폰트 크기 | baseline에서 시각적 상단까지 | baseline에서 시각적 하단까지 |
| --- | --- | --- |
| 17px (card-title) | 13px 위 | 4px 아래 |
| 14px (body) | 10px 위 | 3px 아래 |
| 13px (caption) | 10px 위 | 3px 아래 |

**계산 식**:

상단 여백 12~13px을 목표로 첫 텍스트 baseline 위치 계산:
- 카드 타이틀(17px)이 첫 줄: `첫 텍스트 baseline = 박스 상단 + 13 + 13 = 박스 상단 + 26`
- 본문(14px)이 첫 줄: `첫 텍스트 baseline = 박스 상단 + 13 + 10 = 박스 상단 + 23`

하단 여백 12~13px을 목표로 박스 하단 위치 계산:
- 마지막이 본문(14px): `박스 하단 = 마지막 baseline + 3 + 12 = 마지막 baseline + 15`
- 마지막이 캡션(13px): `박스 하단 = 마지막 baseline + 3 + 12 = 마지막 baseline + 15`

박스 내부 줄 간격: 18~20px (baseline 간 거리)

#### 검증 방법 (필수)

박스 그릴 때마다 다음을 계산해 확인한다:

```
상단 시각적 여백 = (첫 텍스트 baseline) - (첫 텍스트 baseline 보정값) - (박스 상단 y)
하단 시각적 여백 = (박스 하단 y) - (마지막 텍스트 baseline) - 3
```

두 값이 **모두 12~13px 범위**여야 하며, 두 값의 **차이는 2px 이하**여야 한다. 차이가 그 이상이면 텍스트가 한쪽으로 쏠려 보인다.

#### 예시

본문 4줄짜리 박스 (모두 14px body):
- 박스 상단 y=100
- 첫 baseline: 100 + 23 = **123**
- 둘째 baseline: 123 + 18 = 141
- 셋째 baseline: 141 + 18 = 159
- 넷째 baseline: 159 + 18 = 177
- 박스 하단: 177 + 15 = **192**
- 박스 높이: 92px
- 검증: 상단 여백 = 123 - 10 - 100 = 13px ✓ / 하단 여백 = 192 - 177 - 3 = 12px ✓

카드 타이틀 + 본문 3줄짜리 박스:
- 박스 상단 y=100
- card-title baseline: 100 + 26 = **126**
- 첫 body baseline: 126 + 23 = 149 (card-title→body는 23px 띄움)
- 둘째 body baseline: 149 + 18 = 167
- 셋째 body baseline: 167 + 18 = 185
- 박스 하단: 185 + 15 = **200**
- 박스 높이: 100px
- 검증: 상단 여백 = 126 - 13 - 100 = 13px ✓ / 하단 여백 = 200 - 185 - 3 = 12px ✓

**원칙**: 상하 여백이 동일하지 않으면 박스가 미완성으로 보인다. 박스를 그릴 때마다 반드시 위 검증식으로 계산해 두 여백이 12~13px이고 차이가 2px 이하인지 확인한다.

### 8. 요소 간 간격 (박스끼리, 섹션끼리)

박스 내부 여백은 §7에서 다루었고, 박스 외부의 세로 간격도 일관된 규칙이 필요하다. 간격이 들쭉날쭉하면 같은 그룹인지 다른 섹션인지 시각적으로 헷갈린다.

#### 같은 섹션 내 박스 간 세로 간격: 12~16px

같은 섹션 안의 박스들은 12~16px 간격으로 일관되게 배치한다. 박스 내부 상하 여백(12~13px)과 비슷한 수준이면 박스들이 자연스럽게 한 그룹으로 묶여 보인다. 한 박스만 다른 간격이면 그 박스가 의도치 않게 분리되어 보인다.

**계산**: `다음 박스 상단 y = 이전 박스 하단 y + 14` (기본값 14px 권장)

**검증**: 같은 섹션에 박스가 N개라면 N-1개의 간격이 모두 ±2px 범위 안에 있어야 한다.

#### 섹션 타이틀과 이전 박스 사이 여백: 30~40px (시각적 간격 기준)

새로운 섹션이 시작될 때는 앞 섹션과의 분리감이 필요하다. 박스 간 간격(12~16px)보다 명확히 커야 "여기서부터 새 섹션"이라는 시각적 신호가 된다.

**시각적 간격** 기준: 이전 박스 하단(또는 이전 섹션 마지막 요소 끝)과 **섹션 타이틀 텍스트의 시각적 상단** 사이 거리가 30~40px.

**계산** (section-title 16px 기준, baseline 보정값 13):
```
섹션 타이틀 baseline y = 이전 박스 하단 y + 30~40 + 13
                     = 이전 박스 하단 y + 43~53
```

기본값으로 35px 시각적 간격(타이틀 baseline = 이전 박스 하단 + 48)을 권장.

**예시**:
- 이전 박스 하단 y=142
- 섹션 타이틀 baseline y = 142 + 48 = 190 (시각적 간격 35px)

#### 섹션 타이틀과 그 아래 첫 박스 사이 여백: 14~20px

섹션 타이틀과 그 아래 첫 박스 사이는 새 섹션 내부이므로 박스 간 간격과 비슷하게 좁힌다.

**시각적 간격** 기준: 섹션 타이틀 텍스트의 시각적 하단(baseline + 3)과 다음 박스 상단 사이 14~20px.

**계산**:
```
다음 박스 상단 y = 섹션 타이틀 baseline y + 3 + 14~20
                = 섹션 타이틀 baseline y + 17~23
```

기본값 18px 권장.

#### 안티 패턴

- 같은 섹션 안에서 박스 간 간격이 들쭉날쭉(예: 14px / 14px / 20px) → 마지막 박스만 동떨어져 보임
- 섹션 타이틀과 이전 박스 사이가 박스 간 간격과 같거나 더 좁음 → 섹션 분리감 없음
- 섹션 타이틀이 다음 박스에 너무 붙음 → 타이틀이 박스의 일부처럼 보임

### 9. 화살표

`<defs>` 안에 marker로 정의하고 line에 적용:

```svg
<defs>
  <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
</defs>

<line x1="..." y1="..." x2="..." y2="..." marker-end="url(#arr)"
      style="stroke:rgb(140, 138, 130); stroke-width:1.5; fill:none"/>
```

화살표 색상은 중립 회색 `rgb(140, 138, 130)` 기본.

**화살표 길이**: 박스와 박스 사이 화살표는 너무 길지 않게. **30~40px 정도가 적정**. 100px 이상은 부자연스러우므로 박스 간 세로 간격을 줄인다.

#### 라벨이 있는 가로 화살표 길이

화살표 위 또는 아래에 라벨 텍스트(예: "InternalTrigger", "AckEvent")가 있는 경우, **화살표 길이는 라벨 텍스트 폭 + 양옆 여유 10px씩 = 라벨 폭 + 약 20px**로 잡는다.

라벨보다 화살표가 짧으면 텍스트가 양옆 박스 영역을 침범해 답답해 보이고, 너무 길면 의미 없는 빈 공간이 생긴다.

**계산식**:
```
화살표 길이 ≈ 라벨 텍스트 폭 + 20
박스 간 가로 간격 = 화살표 길이
```

**라벨 텍스트 폭 추정** (caption 13px 기준):
- 문자 1개당 약 7~8px (영문 기준), 한글은 약 13px
- 예: "InternalTrigger" (15자) → 약 100~105px
- 예: "AckEvent" (8자) → 약 55~60px

**예시**:
- 라벨 "InternalTrigger" (약 100px) → 화살표 길이 약 **120px**, 박스 간 간격 120px
- 라벨 "Ack" (약 25px) → 화살표 길이 약 **45px**, 박스 간 간격 45px

**이 규칙은 위의 "박스 간 화살표 30~40px 적정" 가이드보다 우선한다.** 30~40px 가이드는 라벨 없는 단순 연결 화살표 기준이고, 라벨이 있으면 라벨 가독성이 우선이다.

### 10. 접근성 태그 (필수)

루트 `<svg>` 안에 다음 세 요소를 반드시 포함:

```svg
<svg viewBox="..." role="img">
  <title>다이어그램의 한 줄 요약 제목</title>
  <desc>다이어그램이 무엇을 설명하는지 한두 문장</desc>
  ...
</svg>
```

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
    text { font-family: "Anthropic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: rgb(20, 20, 19); }
    .h1 { font-size: 21px; font-weight: 600; }
    .col-head { font-size: 15px; font-weight: 600; fill: rgb(115, 114, 108); }
    .sub { font-size: 14px; font-weight: 400; fill: rgb(115, 114, 108); }
    .sec { font-size: 15px; font-weight: 500; }
    .card-title { font-size: 18px; font-weight: 500; }
    .lbl { font-size: 14px; font-weight: 500; }
    .body { font-size: 14px; font-weight: 400; }
    .caption { font-size: 13px; font-weight: 400; fill: rgb(140, 138, 130); }
    .cap { font-size: 12px; font-weight: 400; }
    .micro { font-size: 10px; font-weight: 400; }
    rect.box { stroke-width: 0.5; }

    /* 박스 색상 */
    .beige { fill: rgb(250, 238, 218); stroke: rgb(133, 79, 11); }
    .blue { fill: rgb(230, 241, 251); stroke: rgb(24, 95, 165); }
    .mint { fill: rgb(225, 245, 238); stroke: rgb(15, 110, 86); }
    .lav { fill: rgb(238, 237, 254); stroke: rgb(83, 74, 183); }
    .coral { fill: rgb(250, 236, 231); stroke: rgb(153, 60, 29); }
    .grey { fill: rgb(247, 246, 244); stroke: rgb(180, 178, 170); }

    /* 텍스트 색상 (각 톤의 진한/연한 페어) */
    .t-beige-d { fill: rgb(99, 56, 6); } .t-beige-l { fill: rgb(133, 79, 11); }
    .t-blue-d { fill: rgb(12, 68, 124); } .t-blue-l { fill: rgb(24, 95, 165); }
    .t-mint-d { fill: rgb(8, 80, 65); } .t-mint-l { fill: rgb(15, 110, 86); }
    .t-lav-d { fill: rgb(60, 52, 137); } .t-lav-l { fill: rgb(83, 74, 183); }
    .t-coral-d { fill: rgb(113, 43, 19); } .t-coral-l { fill: rgb(153, 60, 29); }
    .t-grey-l { fill: rgb(115, 114, 108); } .t-grey-ll { fill: rgb(140, 138, 130); }

    line.arr { fill: none; stroke: rgb(140, 138, 130); stroke-width: 1.5; }
  </style>

  <!-- 콘텐츠 -->
</svg>
```

## 예시 1: 단순 박스 + 라벨

```svg
<svg viewBox="0 0 400 100" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>제어기 모듈</title>
  <desc>차량용 ECU 제어기 모듈의 단순 표현</desc>
  <style>
    text { font-family: "Anthropic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  </style>
  <!-- viewBox 폭 400 → 본문 11px이 적정 (11/400=2.75%, 카드 타이틀은 14px) -->
  <rect x="20" y="20" width="360" height="60" rx="8"
        style="fill:rgb(230, 241, 251); stroke:rgb(24, 95, 165); stroke-width:0.5"/>
  <text x="200" y="56" text-anchor="middle"
        style="font-size:14px; font-weight:500; fill:rgb(12, 68, 124)">
    제어기 모듈
  </text>
</svg>
```

## 예시 2: 2단 비교 (좌/우 컬럼 + 컬럼 헤더)

```svg
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>A 방식 vs B 방식 비교</title>
  <desc>두 방식을 좌우로 나란히 비교하는 2단 레이아웃</desc>
  <style>
    text { font-family: "Anthropic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .col-head { font-size: 15px; font-weight: 600; fill: rgb(115, 114, 108); }
    .card-title { font-size: 18px; font-weight: 500; }
    .body { font-size: 14px; font-weight: 400; }
  </style>

  <!-- 컬럼 헤더 -->
  <text x="40" y="32" class="col-head">A 방식</text>
  <text x="400" y="32" class="col-head">B 방식</text>

  <!-- 좌측 박스 (Coral) -->
  <rect x="20" y="50" width="320" height="120" rx="10"
        style="fill:rgb(250, 236, 231); stroke:rgb(153, 60, 29); stroke-width:0.5"/>
  <text x="40" y="84" class="card-title" fill="rgb(113, 43, 19)">A 방식 제목</text>
  <text x="40" y="116" class="body" fill="rgb(153, 60, 29)">설명 첫 줄</text>
  <text x="40" y="140" class="body" fill="rgb(153, 60, 29)">설명 둘째 줄</text>

  <!-- 우측 박스 (Mint) -->
  <rect x="380" y="50" width="320" height="120" rx="10"
        style="fill:rgb(225, 245, 238); stroke:rgb(15, 110, 86); stroke-width:0.5"/>
  <text x="400" y="84" class="card-title" fill="rgb(8, 80, 65)">B 방식 제목</text>
  <text x="400" y="116" class="body" fill="rgb(15, 110, 86)">설명 첫 줄</text>
  <text x="400" y="140" class="body" fill="rgb(15, 110, 86)">설명 둘째 줄</text>
</svg>
```

박스 폭 320 / viewBox 720 = 44% (가이드 45~48% 근처). 좌우 박스 사이 간격 40px.

## 폴더트리(Folder Tree) 패턴

계층 구조(패키지/컨테이너 트리, AR-PATH, 파일 트리 등)는 **파일 탐색기식 폴더트리**로
그린다. 박스를 쌓는 일반 다이어그램과 달리, 폴더/파일 글리프 + 가이드선 + 우측 개수 칩으로
구성한다. 이 패턴은 **항상 동일한 규격**으로 그려야 트리끼리 톤이 통일된다. 아래 수치를
그대로 따른다(임의 변경 금지).

### 고정 규격 (수치)

| 항목 | 값 |
| --- | --- |
| 행 세로 간격 (텍스트 baseline 간) | **32px** |
| depth 1단계당 들여쓰기 (글리프 left) | **+36px** |
| 노드 이름 텍스트 x | 글리프 left **+24px** |
| 폴더 글리프 top y | 텍스트 baseline **−8px** |
| 파일 글리프 top y | 텍스트 baseline **−11px** |
| 개수 칩 (우측 정렬) | x = viewBox폭 **−18**, `text-anchor="end"` |
| 제목 `.h1` 19px / 부제 `.sub` 13px | y=30 / y=50 |
| viewBox 폭 | 680 기본 (라벨 길면 760~900까지) |
| viewBox 높이 | 50(헤더) + 행수×32 + 50(범례·여백) |

### 글리프 (defs 불필요, 인라인 path)

글리프는 `stroke-width:0.5`. 두 종류만 쓴다.

- **폴더 글리프** (자식을 가진 노드): `M{gx} {by-8} q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z`
- **파일 글리프** (자식 없는 리프): `M{gx} {by-11} h7 l5 5 v9 q0 1.5 -1.5 1.5 h-9 q-1.5 0 -1.5 -1.5 v-12.5 q0 -1.5 1.5 -1.5 z`
  + 접힘선 가이드 `M{gx+7} {by-11} v5 h5`

(`gx`=글리프 left, `by`=노드 텍스트 baseline)

### 노드 색 (역할별, 5톤 팔레트 그대로)

색은 **자식 유무로만** 결정한다(판단·강조 개입 없음 → 누가 그려도 동일).

| 역할 | 글리프 | fill / stroke | 이름 텍스트 |
| --- | --- | --- | --- |
| 루트 (최상위) | 폴더 | mint `rgb(225,245,238)` / `rgb(15,110,86)` | `rgb(8,80,65)` |
| 가지 (자식 보유 = sub·ref·하위컨테이너 있음) | 폴더 | blue `rgb(230,241,251)` / `rgb(24,95,165)` | `rgb(12,68,124)` |
| 리프 (자식 없음 = member만) | 파일 | grey `rgb(247,246,244)` / `rgb(180,178,170)` | 기본 `rgb(20,20,19)` |

→ **폴더는 mint(루트)·blue(가지) 둘뿐, grey는 리프(파일)에만.** 자식이 있으면 트리에서
펼쳤든 개수만 표기했든 무조건 blue 폴더다.

이름은 `.row`(14px / 500). 개수 칩은 `.cnt`(13px / 400 / `rgb(140,138,130)`).

### 가이드선 (`.guide` = stroke `rgb(180,178,170)`, width 1, fill none)

각 부모마다 한 세트:
- **세로선**: x = 부모 글리프 left **+9**. 부모 baseline+6 부터 **마지막 자식의 엘보 y**까지.
- **가로 엘보**: 자식마다 세로선 x → 자식 글리프 left 까지, y = 자식 baseline **−4**.

### 하단 범례 (필수)

쓰인 색의 의미를 글리프+라벨 쌍으로 한 줄 깐다(`.leg` 12px 회색). 예: 루트 / 가지 / 리프.

### 템플릿 (이 모양을 기준으로 복제)

```svg
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>… 폴더 트리 (depth 3)</title>
  <desc>… 계층을 파일 탐색기식 폴더 트리로 표현하며, 각 노드에 개수를 표기한다.</desc>
  <style>
    text { font-family: "Anthropic Sans", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans CJK KR", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: rgb(20,20,19); }
    .h1 { font-size: 19px; font-weight: 600; }
    .sub { font-size: 13px; font-weight: 400; fill: rgb(115,114,108); }
    .row { font-size: 14px; font-weight: 500; }
    .cnt { font-size: 13px; font-weight: 400; fill: rgb(140,138,130); }
    .leg { font-size: 12px; font-weight: 400; fill: rgb(115,114,108); }
    .glyph { stroke-width: 0.5; }
    .guide { stroke: rgb(180,178,170); stroke-width: 1; fill: none; }
  </style>

  <text x="20" y="30" class="h1">… — AR-PATH 폴더 트리</text>
  <text x="20" y="50" class="sub">루트 → 가지 → 리프 (depth 3) · 숫자 = member · ref · sub</text>

  <!-- 가이드선: 부모별 세로 + 자식별 엘보 -->
  <path class="guide" d="M37 90 V336"/>
  <path class="guide" d="M37 112 H60"/>
  <!-- … 자식마다 H 엘보 반복 … -->

  <!-- 루트 (mint 폴더), 글리프 left 28 / 이름 x 52 -->
  <path class="glyph" d="M28 76 q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z" fill="rgb(225,245,238)" stroke="rgb(15,110,86)"/>
  <text x="52" y="84" class="row" fill="rgb(8,80,65)">루트이름</text>

  <!-- 가지 (blue 폴더), 글리프 left 62 / 이름 x 86 / 개수 칩 우측 -->
  <path class="glyph" d="M62 108 q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z" fill="rgb(230,241,251)" stroke="rgb(24,95,165)"/>
  <text x="86" y="116" class="row" fill="rgb(12,68,124)">가지이름</text>
  <text x="662" y="116" text-anchor="end" class="cnt">member 22 · sub 3</text>

  <!-- 리프 (grey 파일), 접힘선 포함 -->
  <path class="glyph" d="M62 233 h7 l5 5 v9 q0 1.5 -1.5 1.5 h-9 q-1.5 0 -1.5 -1.5 v-12.5 q0 -1.5 1.5 -1.5 z" fill="rgb(247,246,244)" stroke="rgb(180,178,170)"/>
  <path class="guide" d="M69 233 v5 h5"/>
  <text x="86" y="244" class="row">리프이름</text>
  <text x="662" y="244" text-anchor="end" class="cnt">member 13</text>

  <!-- 하단 범례 -->
  <path class="glyph" d="M20 368 q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z" fill="rgb(225,245,238)" stroke="rgb(15,110,86)"/>
  <text x="44" y="376" class="leg">루트</text>
</svg>
```

## 안티 패턴 (하지 말 것)

```svg
<!-- ❌ width="100%"는 컨테이너 크기에 따라 0px가 되거나 깨질 수 있다 -->
<svg width="100%" height="100%" viewBox="0 0 800 600">...</svg>

<!-- ❌ viewBox 폭이 큰데 폰트는 작게 (글자가 매우 작아 보임) -->
<svg viewBox="0 0 1200 800">
  <text font-size="11">...</text>  <!-- 11/1200 = 0.9%, 너무 작음 -->
</svg>

<!-- ❌ 본문을 12px 미만으로 (가독성 급락) -->
<text font-size="9" class="body">중요한 본문 텍스트</text>

<!-- ❌ 박스가 글자 줄 수에 비해 너무 큼 (휑함) -->
<rect width="300" height="200" .../>
<text>제목</text>
<text>한 줄 본문</text>
<!-- 본문 1줄인데 박스 높이 200px → 80px가 적정 -->

<!-- ❌ 상하 여백이 다름 (텍스트가 한쪽으로 쏠려 보임) -->
<rect x="20" y="42" width="680" height="195" .../>
<text x="40" y="68" class="card-title">...</text>  <!-- 상단 여백 13px -->
<text x="40" y="232" class="body">마지막 줄</text>  <!-- 하단 여백 2px ❌ -->
<!-- 하단 여백을 12~13px로 맞추려면 박스 height 또는 마지막 baseline 조정 -->

<!-- ❌ baseline 기준으로만 여백을 잼 (폰트 크기가 다르면 시각적 여백이 어긋남) -->
<rect y="42" height="200" .../>
<text y="62">card-title</text>   <!-- baseline-박스상단 = 20px이지만 시각적으로는 7px -->
<text y="222">마지막 본문</text>  <!-- baseline-박스하단 = 20px이지만 시각적으로는 17px -->
<!-- baseline이 아니라 §7의 시각적 여백 계산식을 써야 함 -->

<!-- ❌ 굵은 테두리 (stroke-width 2 이상) -->
<rect stroke-width="2" .../>

<!-- ❌ 진한 채도 직접 사용 (#1e3a8a, #f59e0b 같은 hex 코드) -->
<rect fill="#1e3a8a"/>

<!-- ❌ accessibility 태그 없음 -->
<svg viewBox="...">
  <!-- title, desc 없이 바로 콘텐츠 -->
</svg>

<!-- ❌ font-family 누락 -->
<svg viewBox="0 0 400 120">
  <text>제어기 모듈</text>
</svg>

<!-- ❌ 화살표가 너무 김 (박스 간격이 과도) -->
<line x1="100" y1="100" x2="100" y2="250" marker-end="url(#arr)"/>
<!-- 150px 화살표 → 박스 간격을 좁혀 30~40px로 -->
```

## 체크리스트

SVG를 출력하기 전 다음을 모두 확인한다:

- [ ] 루트 `<svg>`에 `viewBox`가 있고 `width="100%"`가 **없다**.
- [ ] viewBox 폭은 **720이 기본** (좁은 도식은 400~600).
- [ ] `role="img"`, `<title>`, `<desc>` 3종 세트가 있다.
- [ ] `<style>` 블록에 폰트 스택과 색상 클래스가 정의되어 있다.
- [ ] 폰트 스택 첫 항목은 `"Anthropic Sans"`.
- [ ] **본문 폰트 크기 / viewBox 폭 ≈ 2.0~2.3%** (예: viewBox 720 → body 14~16px).
- [ ] **본문 폰트는 12px 미만으로 내려가지 않는다** (밀도 높은 표 등 예외 제외).
- [ ] 카드 타이틀은 18~21px, 두께 500~600.
- [ ] 컬럼 헤더가 있다면 15px / 600 / 회색.
- [ ] 박스 높이가 글자 줄 수에 비례하고, **상단 시각적 여백과 하단 시각적 여백이 모두 12~13px이며 차이가 2px 이하**다 (§7 검증식으로 계산).
- [ ] **같은 섹션 내 박스 간 세로 간격이 12~16px로 일관**된다 (모든 간격이 ±2px 범위, §8).
- [ ] **섹션 타이틀과 이전 박스 사이 시각적 간격이 30~40px**이다 (박스 간 간격보다 명확히 커야 섹션 분리감, §8).
- [ ] **섹션 타이틀과 그 아래 첫 박스 사이 시각적 간격이 14~20px**이다 (§8).
- [ ] 박스 fill/stroke는 5톤 파스텔 팔레트(beige/blue/mint/lav/coral) 또는 grey의 정확한 RGB 값을 사용한다.
- [ ] 모든 rect의 stroke-width는 0.5다.
- [ ] 박스 모서리는 rx 4/6/8/10 규격을 따른다.
- [ ] 화살표는 `<defs>` marker로 정의되어 있고, 길이는 30~40px 정도.
- [ ] 화살표 위/아래에 **라벨이 있다면 화살표 길이 ≥ 라벨 폭 + 20px** (§9, 30~40px 가이드보다 우선).
- [ ] **계층/트리를 그린다면 「폴더트리 패턴」 규격을 그대로 따랐다** — 폴더·파일 글리프, 행 간격 32 / 들여쓰기 36, 루트=mint·가지=blue·리프=grey 색, 가이드선, 우측 개수 칩, 하단 범례.

## 적용 범위

이 규칙은 다음 모든 경우에 적용한다:

- 독립 `.svg` 파일 생성
- HTML 문서 안의 인라인 `<svg>` 마크업
- React/JSX 컴포넌트 안의 `<svg>` 엘리먼트
- Confluence 페이지 첨부용 SVG (`confluence-writing` 스킬과 함께 쓰일 때)
- 포트폴리오/문서 삽입용 다이어그램 (`portfolio-theme` 스킬과 함께 쓰일 때)
- `visualize:show_widget`으로 SVG 모드로 렌더링하는 코드

다른 SVG 관련 디자인 규칙(특수 도메인 컬러 등)이 다른 스킬에서 정의되어 있다면 그 규칙과 병행해 적용한다.
