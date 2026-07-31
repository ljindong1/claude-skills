# 패턴 라이브러리

자주 그리는 다이어그램 유형의 **고정 규격**. 해당 유형을 그릴 때는 이 규격을 그대로 따른다(임의 변경 금지). 규격이 있으면 매번 다르게 그려져 톤이 흔들리는 것을 막고, 즉흥적 "박스 나열"로 환원되는 것을 방지한다.

모든 패턴은 SKILL.md의 핵심 규칙(§1~§10), 표현 장치(§11), 가드레일(§12)을 전제로 한다.

## 목차

1. [레이어 스택](#1-레이어-스택) — SW 계층 구조 (AUTOSAR 등)
2. [파이프라인 / 플로우](#2-파이프라인--플로우) — 순서 있는 처리 단계
3. [시퀀스 다이어그램](#3-시퀀스-다이어그램) — 모듈 간 호출/메시지 순서
4. [상태머신](#4-상태머신) — 상태 전이
5. [스윔레인](#5-스윔레인) — 담당 주체별 프로세스
6. [폴더트리](#6-폴더트리) — 계층 구조 (패키지/AR-PATH/파일)
7. [2단 비교](#7-2단-비교) — 좌/우 대조

---

## 1. 레이어 스택

SW 계층 구조(AUTOSAR ASW/RTE/BSW/MCAL/HW, OSI 스택 등)를 전폭 가로 밴드를 쌓아 표현한다.

### 고정 규격

| 항목 | 값 |
| --- | --- |
| viewBox 폭 | 720 |
| 레이어 밴드 폭 | 680 (x=20~700) |
| 레이어 높이 (라벨만) | **44px** |
| 레이어 높이 (내부 모듈 칩 포함) | **72px** |
| 레이어 높이 (얇은 종단 레이어 — HW, 물리 매체 등) | **24~28px**, 라벨 `.cap` 12px |
| 레이어 간 세로 간격 | **6px** (스택이므로 §8보다 좁게 — 밀착감이 계층의 인접성을 표현) |
| 레이어 라벨 | 좌측 x=44, `.lbl` 15px/500, 세로 중앙 (`dominant-baseline="central"`) |
| 내부 모듈 칩 | 높이 28, rx 6, `.cap` 12px/500, 좌우 패딩 12, 칩 간 간격 10, 레이어 세로 중앙 정렬. 라벨 영역 확보를 위해 x=180부터 배치. **fill은 흰색 `rgb(255,255,255)`** + 레이어 톤 stroke 0.5 + 톤 진한 텍스트 — 레이어 배경과 같은 fill이면 구분이 약하다(렌더링 검증됨) |
| 레이어 rx | 8 |

### 톤 매핑 (AUTOSAR 기준 — 다른 스택도 역할 유추해 매핑)

| 레이어 | 톤 |
| --- | --- |
| ASW (Application) | Lavender |
| RTE | Grey |
| BSW Services | Blue |
| ECU Abstraction | Mint |
| MCAL | Beige |
| Hardware | Grey (라벨은 `.t-grey-l`) |

유채색 3톤 초과가 되면(위처럼 4톤 필요하면) 스택 패턴은 예외로 허용한다 — 계층별 색이 곧 범례이기 때문. 대신 하단에 색 범례는 달지 않는다(레이어 라벨이 범례 역할).

### 강조

- 설명 대상 레이어 하나만 hero: stroke-width 1, 해당 레이어의 관련 모듈 칩 하나에 상태 칩(mint "핵심") 허용.
- 레이어 옆(우측 바깥)에 caption으로 주석을 달 때는 leader 점선(`.arr-sub` 색, dasharray 2 2, width 0.75)으로 연결.

### 템플릿 (요지)

```svg
<!-- 레이어 하나 (모듈 칩 포함형, 상단 y=Y). 칩은 흰색 fill -->
<rect x="20" y="{Y}" width="680" height="72" rx="8" class="blue box"/>
<text x="44" y="{Y+36}" dominant-baseline="central" class="lbl t-blue-d">BSW Services</text>
<rect x="180" y="{Y+22}" width="76" height="28" rx="6" style="fill:rgb(255,255,255); stroke:rgb(24,95,165); stroke-width:0.5"/>
<text x="218" y="{Y+36}" text-anchor="middle" dominant-baseline="central" class="cap t-blue-d">Com</text>
<rect x="266" y="{Y+22}" width="86" height="28" rx="6" style="fill:rgb(255,255,255); stroke:rgb(24,95,165); stroke-width:0.5"/>
<text x="309" y="{Y+36}" text-anchor="middle" dominant-baseline="central" class="cap t-blue-d">PduR</text>
<!-- 다음 레이어 상단 = Y + 72 + 6 -->
```

관통 요소(예: Complex Driver가 여러 레이어를 세로로 가로지름)는 스택 우측에 세로 rect(폭 90~110, 높이 = 걸치는 레이어들의 총 높이)로 겹치지 않게 옆에 세운다.

---

## 2. 파이프라인 / 플로우

빌드 파이프라인, 처리 단계, 절차 흐름. **가로 방향 + 번호 배지**가 기본.

### 고정 규격

| 항목 | 값 |
| --- | --- |
| 방향 | 가로 (단계 5개 이하) / 세로 (6개 이상 또는 각 단계 설명이 2줄 이상) |
| 스텝 카드 폭 (가로형) | `(viewBox폭 − 40 − 화살표총폭) / N`, 화살표 하나당 36px |
| 스텝 카드 높이 | 타이틀만 64 / 타이틀+본문 1줄 88 (§7 계산식 적용) |
| 번호 배지 | §11-4 규격 (r=11, 톤 stroke fill, 흰 텍스트). 카드 내부 좌상단 |
| 카드 간 화살표 | 주 흐름 실선 36px, 세로 중앙 |
| 카드 rx | 8 |

### 톤 배정

단계를 무지개로 칠하지 않는다. 기본은 **전 단계 동일 톤**(예: blue) + 최종 산출 단계만 mint, 실패/예외 분기만 coral. 분기가 있으면 분기 화살표는 점선(`.arr-sub`).

### 세로형

카드 폭 45~48%(§4), 좌측 정렬로 쌓고 카드 간 세로 간격 14px + 화살표 없이 좌측에 **연속 액센트 바** 대신 각 카드 번호 배지로 순서 표현. 카드 간 화살표가 필요하면 30px 간격 + 화살표.

### 템플릿 (요지, 4단계 가로형: 카드 폭 (720−40−108)/4 = 143)

```svg
<rect x="20" y="80" width="143" height="88" rx="8" class="blue box"/>
<circle cx="44" cy="101" r="11" fill="rgb(24,95,165)"/>
<text x="44" y="101" text-anchor="middle" dominant-baseline="central" class="chip-txt t-white">1</text>
<text x="64" y="106" class="lbl t-blue-d">컴파일</text>
<text x="40" y="134" class="cap t-blue-l">gcc -O2</text>
<line x1="167" y1="124" x2="199" y2="124" class="arr" marker-end="url(#arr)"/>
<!-- 다음 카드 x = 20 + 143 + 36 = 199 -->
```

---

## 3. 시퀀스 다이어그램

모듈/태스크 간 호출·메시지 순서 (예: CanIf → CanDrv 송신 경로, RTE 이벤트 전달).

### 고정 규격

| 항목 | 값 |
| --- | --- |
| viewBox 폭 | 참여자 3개 720 / 4개 900 / 5개 1000 (§4 폰트 비율 재계산 필수) |
| 참여자(actor) 헤더 카드 | 폭 132, 높이 40, rx 8, 타이틀 `.lbl` 세로 중앙·가로 중앙 |
| lifeline 간격 (중심 간) | **≥ 180px** (메시지 라벨이 들어갈 폭) |
| lifeline | 헤더 하단부터 세로 점선 — stroke `rgb(180,178,170)`, width 0.75, dasharray 4 4 |
| 메시지 세로 간격 | **46px** (라벨 baseline 간) |
| 메시지 (호출) | 주 흐름 실선 + 화살표, 라벨은 화살표 **위 6px**, `.caption`, 화살표 중앙 정렬 |
| 메시지 (응답/비동기) | 점선 `.arr-sub` |
| activation bar | lifeline 위 rect 폭 **8**, 해당 구간 높이, 참여자 톤의 박스 fill + stroke 0.5 |
| self-call | lifeline에서 우측으로 폭 40의 ㄷ자 path (`fill="none"`) + 라벨 우측 |

### 톤 배정

참여자 헤더 카드에 역할 톤(호출 시작자 beige/입력, 처리자 blue, 최종 도달 모듈 mint 등). lifeline·메시지는 중립 회색 유지 — 색은 참여자에만.

### 순서 표기

메시지가 6개 이상이면 각 메시지 라벨 앞에 `1.` `2.` 번호를 붙인다 (배지 아님, 텍스트).

### 템플릿 (요지)

```svg
<!-- 참여자 헤더 (x중심 C, 상단 y=20) -->
<rect x="{C-66}" y="20" width="132" height="40" rx="8" class="blue box"/>
<text x="{C}" y="40" text-anchor="middle" dominant-baseline="central" class="lbl t-blue-d">CanIf</text>
<line x1="{C}" y1="60" x2="{C}" y2="{하단}" stroke="rgb(180,178,170)" stroke-width="0.75" stroke-dasharray="4 4"/>
<!-- activation bar -->
<rect x="{C-4}" y="{t1}" width="8" height="{t2-t1}" class="blue box"/>
<!-- 메시지: A(중심 Ca) → B(중심 Cb), y=M -->
<text x="{(Ca+Cb)/2}" y="{M-6}" text-anchor="middle" class="caption">Can_Write(hth, pdu)</text>
<line x1="{Ca+4}" y1="{M}" x2="{Cb-4}" y2="{M}" class="arr" marker-end="url(#arr)"/>
```

---

## 4. 상태머신

상태 전이 (예: CAN 컨트롤러 STOPPED/STARTED/SLEEP, 통신 상태 FULL/SILENT/NO_COM).

### 고정 규격

| 항목 | 값 |
| --- | --- |
| 상태 노드 | rounded rect, rx **14** (일반 카드 8~10과 구분되는 pill에 가까운 형태), 높이 44 (이름만) / 64 (이름+entry 액션 1줄) |
| 상태 이름 | `.lbl` 15px/500, 가로·세로 중앙 |
| 시작점 | 채운 원 r=6, fill `rgb(115,114,108)` + 첫 상태로 실선 화살표 |
| 종료점 | 이중 원 — 바깥 r=8 stroke만, 안쪽 r=4.5 fill, 색 동일 `rgb(115,114,108)` |
| 전이 화살표 | 주 흐름 실선. 역방향/예외 전이는 점선. 교차 금지 — 필요하면 L자 우회 (§9) |
| 전이 라벨 | `.caption`, 형식 `이벤트 [가드] / 액션` 중 있는 것만. 가로 전이는 화살표 위 6px, 세로 전이는 화살표 우측 8px |
| 상태 간 간격 | 라벨 폭 + 20 (§9 라벨 규칙) — 최소 60px |

### 톤 배정

정상 운영 상태 mint, 초기화/중간 상태 blue, 오류/버스오프 상태 coral, 슬립/비활성 grey. 시작·종료점은 항상 중립 회색.

### 배치

상태 5개 이하: 가로 1열 또는 2×2 + 전이. 6개 이상: 주 경로(happy path)를 왼→오 1열로 놓고 예외 상태를 아래 행에 배치, 예외 전이는 점선.

---

## 5. 스윔레인

담당 주체(팀/모듈/코어)별로 프로세스를 나눠 보일 때.

### 고정 규격

| 항목 | 값 |
| --- | --- |
| 방향 | 가로 레인 (레인 = 행) |
| viewBox 폭 | 900~1000 (§4 폰트 비율 재계산) |
| 레인 라벨 컬럼 | 좌측 폭 **110** — 레인 틴트보다 살짝 진하게: 톤 박스 fill + 레인 본체는 존 틴트. 라벨 `.lbl` 세로 중앙, x=레인좌+16 (회전 텍스트 금지) |
| 레인 본체 | 그룹 존 규격(§11-3)의 변형 — 존 틴트 fill, stroke 0.5 **실선**(dashed 아님 — 레인 경계는 명확해야 함), rx 0 (레인끼리 밀착), 전체 외곽만 rx 12 |
| 레인 높이 | 내부 카드 1행 기준 100 (카드 64 + 상하 18) |
| 레인 간 구분 | 레인 사이 간격 0, 경계선 공유 |
| 내부 스텝 카드 | 파이프라인 규격(§2) 카드 + 번호 배지, 레인을 넘나드는 화살표는 세로/L자 |

### 톤 배정

레인당 1톤(존 틴트 + 라벨 컬럼 박스 fill). 유채색 3톤 이하 원칙 적용 — 레인 4개 이상이면 일부 레인은 grey.

---

## 6. 폴더트리

계층 구조(패키지/컨테이너 트리, AR-PATH, 파일 트리)는 파일 탐색기식 폴더트리로 그린다. **항상 동일 규격**(임의 변경 금지).

### 고정 규격 (수치)

| 항목 | 값 |
| --- | --- |
| 행 세로 간격 (baseline 간) | **32px** |
| depth 1단계당 들여쓰기 (글리프 left) | **+36px** |
| 노드 이름 텍스트 x | 글리프 left **+24px** |
| 폴더 글리프 top y | baseline **−8px** |
| 파일 글리프 top y | baseline **−11px** |
| 개수 칩 (우측 정렬) | x = viewBox폭 **−18**, `text-anchor="end"` |
| 제목 `.h1` 19px / 부제 `.sub` 13px | y=30 / y=50 |
| viewBox 폭 | 680 기본 (라벨 길면 760~900) |
| viewBox 높이 | 50(헤더) + 행수×32 + 50(범례·여백) |

### 글리프 (defs 불필요, 인라인 path, stroke-width 0.5)

- **폴더** (자식 보유): `M{gx} {by-8} q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z`
- **파일** (리프): `M{gx} {by-11} h7 l5 5 v9 q0 1.5 -1.5 1.5 h-9 q-1.5 0 -1.5 -1.5 v-12.5 q0 -1.5 1.5 -1.5 z` + 접힘선 `M{gx+7} {by-11} v5 h5`

(`gx`=글리프 left, `by`=baseline)

### 노드 색 (자식 유무로만 결정 — 판단 개입 없음)

| 역할 | 글리프 | fill / stroke | 이름 텍스트 |
| --- | --- | --- | --- |
| 루트 | 폴더 | mint `rgb(225,245,238)` / `rgb(15,110,86)` | `rgb(8,80,65)` |
| 가지 (자식 보유) | 폴더 | blue `rgb(230,241,251)` / `rgb(24,95,165)` | `rgb(12,68,124)` |
| 리프 (자식 없음) | 파일 | grey `rgb(247,246,244)` / `rgb(180,178,170)` | 기본 `rgb(20,20,19)` |

폴더는 mint(루트)·blue(가지) 둘뿐, grey는 리프에만. 자식이 있으면 무조건 blue 폴더다.

이름 `.row`(14px/500), 개수 칩 `.cnt`(13px/400/`rgb(140,138,130)`).

### 가이드선 (`.guide` = stroke `rgb(180,178,170)`, width 1, fill none)

- **세로선**: x = 부모 글리프 left **+9**, 부모 baseline+6 → 마지막 자식 엘보 y
- **가로 엘보**: 세로선 x → 자식 글리프 left, y = 자식 baseline **−4**

### 하단 범례 (필수)

쓰인 색의 의미를 글리프+라벨 쌍으로 한 줄 (`.leg` 12px 회색). 예: 루트 / 가지 / 리프.

### 템플릿

```svg
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>… 폴더 트리 (depth 3)</title>
  <desc>… 계층을 파일 탐색기식 폴더 트리로 표현하며, 각 노드에 개수를 표기한다.</desc>
  <style>
    text { font-family: "현대하모니 M", "HDharmony M", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans CJK KR", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: rgb(20,20,19); }
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

  <path class="guide" d="M37 90 V336"/>
  <path class="guide" d="M37 112 H60"/>

  <path class="glyph" d="M28 76 q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z" fill="rgb(225,245,238)" stroke="rgb(15,110,86)"/>
  <text x="52" y="84" class="row" fill="rgb(8,80,65)">루트이름</text>

  <path class="glyph" d="M62 108 q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z" fill="rgb(230,241,251)" stroke="rgb(24,95,165)"/>
  <text x="86" y="116" class="row" fill="rgb(12,68,124)">가지이름</text>
  <text x="662" y="116" text-anchor="end" class="cnt">member 22 · sub 3</text>

  <path class="glyph" d="M62 233 h7 l5 5 v9 q0 1.5 -1.5 1.5 h-9 q-1.5 0 -1.5 -1.5 v-12.5 q0 -1.5 1.5 -1.5 z" fill="rgb(247,246,244)" stroke="rgb(180,178,170)"/>
  <path class="guide" d="M69 233 v5 h5"/>
  <text x="86" y="244" class="row">리프이름</text>
  <text x="662" y="244" text-anchor="end" class="cnt">member 13</text>

  <path class="glyph" d="M20 368 q0 -3 3 -3 h5 l2 2 h5 q3 0 3 3 v6 q0 3 -3 3 h-15 q-3 0 -3 -3 z" fill="rgb(225,245,238)" stroke="rgb(15,110,86)"/>
  <text x="44" y="376" class="leg">루트</text>
</svg>
```

---

## 7. 2단 비교

두 방식/구조를 좌우 대조. 박스 폭 45~48%(§4), 좌우 간격 40px, 각 컬럼 상단에 `.col-head`(15px/600/회색).

톤 배정: 비교가 우열이면 열세 coral / 우세 mint. 중립 비교면 blue / lavender. 행이 여러 개면 같은 행끼리 높이를 맞추고 §8 간격 규칙 적용.

```svg
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>A 방식 vs B 방식 비교</title>
  <desc>두 방식을 좌우로 나란히 비교하는 2단 레이아웃</desc>
  <style>
    text { font-family: "현대하모니 M", "HDharmony M", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .col-head { font-size: 15px; font-weight: 600; fill: rgb(115, 114, 108); }
    .card-title { font-size: 18px; font-weight: 500; }
    .body { font-size: 14px; font-weight: 400; }
  </style>

  <text x="40" y="32" class="col-head">A 방식</text>
  <text x="400" y="32" class="col-head">B 방식</text>

  <rect x="20" y="50" width="320" height="120" rx="10"
        style="fill:rgb(250, 236, 231); stroke:rgb(153, 60, 29); stroke-width:0.5"/>
  <text x="40" y="84" class="card-title" fill="rgb(113, 43, 19)">A 방식 제목</text>
  <text x="40" y="116" class="body" fill="rgb(153, 60, 29)">설명 첫 줄</text>
  <text x="40" y="140" class="body" fill="rgb(153, 60, 29)">설명 둘째 줄</text>

  <rect x="380" y="50" width="320" height="120" rx="10"
        style="fill:rgb(225, 245, 238); stroke:rgb(15, 110, 86); stroke-width:0.5"/>
  <text x="400" y="84" class="card-title" fill="rgb(8, 80, 65)">B 방식 제목</text>
  <text x="400" y="116" class="body" fill="rgb(15, 110, 86)">설명 첫 줄</text>
  <text x="400" y="140" class="body" fill="rgb(15, 110, 86)">설명 둘째 줄</text>
</svg>
```
