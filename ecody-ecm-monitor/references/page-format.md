# 일일 모니터링 페이지 형식 (정본)

`createConfluencePage`에 `contentFormat="html"`로 보낸다. 헤더는 H3부터. 표는 `<colgroup>` 없이 모든 셀에 `data-colwidth`, `<table data-layout="default" data-display-mode="fixed">`. 기준 폭 760.

## 링크 규칙

| 용도 | URL |
| --- | --- |
| 페이지 | `https://ecody-ecm.autoever.com/pages/viewpage.action?pageId=<id>` |
| 비교(diff를 읽은 경우) | `https://ecody-ecm.autoever.com/pages/diffpagesbyversion.action?pageId=<id>&selectedPageVersions=<base>&selectedPageVersions=<cur>` |
| 이력(읽지 않은 MOD) | `https://ecody-ecm.autoever.com/pages/viewpreviousversions.action?pageId=<id>` |

제목 셀은 페이지 링크로 건다. 사내 위키에서 링크를 누르면 오토에버 로그인이 필요하다는 점은 푸터에 한 번 적는다.

## 본문 골격

```html
<blockquote>
  <p>📌 <strong>수집 개요</strong></p>
  <p>구간: 2026-09-14 (월) 09:30 ~ 2026-09-15 (화) 08:00 KST · 신규 3 · 수정 43 · 이미지 첨부 25건 제외</p>
  <p>공지 1 · IA 37 · SAG 5 · UM 3</p>
</blockquote>

<blockquote>
  <p>💡 <strong>오늘의 핵심</strong></p>
  <ul>
    <li>[공지] BSW 정기 릴리즈 계획에 SecOC R44 2.0.0.0_HF6, FiM 2.0.2.0 추가</li>
    <li>[SAG 신규] INCA Prof 리프로그래밍 절차(ETAS 라이선스·ES582·S32K56 교차인증) 가이드 등록</li>
    <li>[SAG] CYTxx StartUp Wdg Timer 가이드에 wdt_wait 코드 추가 사유(1.3 주의사항) 신설</li>
  </ul>
</blockquote>

<h3>📢 공지 (NOTICE)</h3>
<table data-layout="default" data-display-mode="fixed">
  <thead><tr>
    <th data-colwidth="70"><p><strong>구분</strong></p></th>
    <th data-colwidth="230"><p><strong>제목</strong></p></th>
    <th data-colwidth="300"><p><strong>변경 요약</strong></p></th>
    <th data-colwidth="160"><p><strong>작성자 · 시각 · 태그</strong></p></th>
  </tr></thead>
  <tbody><tr>
    <td data-colwidth="70"><p>🔄 수정</p></td>
    <td data-colwidth="230"><p><a href="…">Regular Releases Plan (BSW Module, C Studio)</a></p></td>
    <td data-colwidth="300"><p>SecOC R44 2.0.0.0_HF6, FiM 2.0.2.0 릴리즈 항목 추가 (<a href="…diff…">비교</a>)</p></td>
    <td data-colwidth="160"><p>양효언 · 09-15 09:21</p></td>
  </tr></tbody>
</table>
```

## 섹션 이름과 이모지 (고정)

| 그룹 | H3 |
| --- | --- |
| NOTICE | `📢 공지 (NOTICE)` |
| POLICY | `📘 Policy` |
| IA | `✅ Integration Auditor 규칙 (IA)` |
| VC | `🔍 Validation Checker 규칙 (VC)` |
| SAG | `🛠️ SW Application Guide (SAG)` |
| IM | `🔧 Integration Manual (IM)` |
| UM | `📝 R44 User Manual (UM)` |
| CSTUDIO | `📚 C Studio Manual` |
| OTHER | `🗂️ 기타 공간 (FoD · m.Security · Tool Chain)` |
| MISC | `📦 분류 외` |
| 비이미지 첨부 | `📎 배포 파일·문서 첨부` |

구분 칸: `🆕 신규` / `🔄 수정` / `💬 댓글`. 각 섹션 안에서는 신규 먼저, 그다음 최근 시각순.

## 칸 채우기 규칙

- **변경 요약**: 한두 문장. 무엇이 추가·변경·삭제됐는지를 사실로 쓴다. 본문 문장 복사 금지, 설정값·버전·파라미터명은 그대로 써도 된다.
  - NEW + body 읽음 → 목적·대상(MCU/모듈/버전)·핵심 절차를 요약.
  - MOD + diff 읽음 → 바뀐 점만.
  - 읽지 않은 MOD → 버전메시지가 있으면 그대로(짧게), 없으면 `내용 수정 (v12 → 이력)`.
- **작성자**: 팀 표기(`/클래식오토사1팀`)는 빼고 이름만. 섹션 첫 등장에만 팀을 붙여도 된다.
- **태그**: 수집기 태그를 쉼표로. 비어 있으면 `-`.
- SAG·IM·UM 행에는 제목 앞에 하위분류를 작게 붙인다: `[9. WatchDog]`, `[UM - Communication]`.

## 일괄 편집 접기

같은 그룹·같은 작성자·같은 버전메시지 MOD가 3건 이상이면 한 행:

| 구분 | 제목 | 변경 요약 | 작성자 · 시각 · 태그 |
| --- | --- | --- | --- |
| 🔄 수정 ×27 | IA-063~094 중 27건 | "N/A·UserCheck 코드 조건/출력 메시지 표 반영" 일괄 적용. 대상: IA-063, 064, …, 094 | 김덕환 · 09-15 09:28~09:29 |

접은 행 아래에 개별 행을 두지 않는다. 메시지가 없는 일괄 수정(같은 작성자가 1시간 안에 5건 이상)도 같은 방식으로 접되 요약에 "개별 내용 미확인"을 적는다.

## 이미지 첨부

표로 만들지 않는다. 푸터에 한 줄: `이미지 첨부 25건 제외 (KeyM - 5. Generator 17, INCA Prof 리프로그래밍 2 …)` — 상위 5개 컨테이너만.

## 변경 없음

rows = 0이면 개요 박스에 `구간 내 변경 없음`만 쓰고 섹션 없이 푸터로 간다. 페이지는 **반드시 만든다**(구간 사슬 유지).

## 감사 푸터 (글자 그대로)

```html
<hr/>
<p><em>수집 원시: page 225 · blogpost 0 · comment 0 · attachment 186 (하루 여유 조회분) → 구간 내 rows 46 = 게재 46 · 이미지 첨부 25건 제외</em></p>
<p><em>정독: body 2 · diff 7 · 조회 실패 0 · 링크는 eCoDY-ECM 로그인 필요</em></p>
<p><em>ECM-WINDOW-START-UTC: 2026-09-14T15:00:00Z</em></p>
<p><em>ECM-WINDOW-END-UTC: 2026-09-15T02:30:00Z</em></p>
```

원장 반영에 실패한 그룹이 있으면 `ECM-WINDOW-START-UTC` 줄 앞에 `<p><em>ECM-LEDGER-PENDING: SAG, IM</em></p>`가 추가된다(`ledger.md` §5). 전부 반영되면 이 줄은 없다.

마커 두 줄은 다음 실행이 정규식 `ECM-WINDOW-END-UTC:\s*(\S+)`로 읽는다. 형식을 바꾸지 않는다.
