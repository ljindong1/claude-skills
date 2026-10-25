# 알려진 함정

실제 이관 작업에서 관찰된 것들. 증상을 만나면 여기를 본다.

## 1. 빈 껍데기 페이지

**증상**: 하위 목록에는 있는데 `body.storage.value`가 `"<p />"` 또는 `""`.

트리 정리용으로 만들어두고 내용을 안 채운 페이지가 흔하다. 하위 페이지도 없는 경우가 많다.

**대응**: 목록 제시 단계에서 본문 유무를 표시해 미리 걸러낸다. 기본은 제외하되, 트리 구조상 자리가 필요하면 사용자에게 물어 빈 페이지로 만든다. 조용히 건너뛰지 말고 완료 보고에 "원본이 빈 페이지라 제외"로 남긴다.

## 2. 글자가 안 보이는 페이지

**증상**: 발행 후 특정 구간의 텍스트가 보이지 않는다. 되읽어 보면 `<span style="color: #fedec8">`처럼 글자색이 배경색 값으로 들어가 있다.

원인은 원본의 형광펜(background-color)이다. storage-to-html.md §2 참조.

**대응**: 처음부터 `<strong>`으로 넣는다. 이미 발행됐다면 수정 워크플로우(허락 + 직전 fetch + 전체 body 재전송)로 고친다.

## 3. 줄바꿈으로 뭉친 목록

**증상**: 원본이 `<p>` 하나에 `<br />`로 수십 줄을 밀어넣은 형태. 항목과 설명의 짝이 어긋나 있다.

외부 치트시트를 붙여넣은 페이지에서 자주 나온다. 예:

```
Ctrl+G
Go to Line... Ctrl+P Go to File...
```

**대응**: 짝을 바로잡아 한 줄에 하나씩 정리한다. 내용을 추가하거나 삭제하지 않는다. **완료 보고에 "어느 섹션의 줄을 정리했다"고 반드시 밝힌다** — 원본과 달라진 부분이므로 사용자가 알아야 한다.

의미가 불분명해 짝을 확신할 수 없으면 원본 그대로 두고 보고에 남긴다.

## 4. 깨진 인라인 코드

**증상**: 원본에 ``Ctrl+<code> ... Ctrl+Shift+</code>`` 처럼 백틱 처리가 어긋난 흔적.

원본 작성 시 백틱이 잘못 닫힌 것이다.

**대응**: 의도가 명확하면(예: 터미널 단축키의 백틱 키) 정상화하고 보고한다. 불분명하면 그대로 둔다.

## 5. 배치 navigate 실패

**증상**: `browser_batch cannot act on a page after navigating to it` 또는 `must act on one tab`.

**대응**: navigate는 단독 호출, 배치는 한 tabId만. 두 탭을 오가는 작업은 탭마다 배치를 따로 보낸다.

## 6. 사용자가 브라우저 접근을 거부

**증상**: `Permission denied by user`.

실수로 눌렀을 수도 있고 중단 의도일 수도 있다.

**대응**: 재시도하지 않는다. 현재까지 완료/남은/제외 목록을 정리해 보고하고 계속할지 묻는다.

## 7. 타겟 대표 페이지가 이미 있고 비어 있음

사용자가 미리 껍데기 페이지를 만들어두고 URL을 주는 경우가 흔하다.

**대응**: 비어 있어도 **create가 아니라 update**다. 별도 허락을 받고, update 직전에 `getConfluencePage`로 최신 본문·version을 확인한다. version이 예상과 다르면 사용자가 직접 편집한 것이므로 보존 대상을 파악한다.

## 8. 트리가 예상보다 큼

직계 하위가 20개를 넘거나 손자 세대가 깊은 경우.

**대응**: 목록을 보여준 뒤 소요(페이지당 읽기 2회 + 발행 1회)를 알리고 범위를 좁힐지 묻는다. 중간에 컨텍스트가 부족해지면 완료 지점을 명확히 보고하고, 재개 시 타겟 트리를 먼저 조회해 이미 만들어진 페이지를 건너뛴다.

## 9. 정렬 순서

`child/page` 응답의 `extensions.position` 값이 원본 트리의 정렬 순서다. 응답 배열 순서를 그대로 따르면 원본과 같은 순서가 된다.

타겟에서 순서가 다르게 보이면 Confluence의 정렬 설정(수동/알파벳순) 차이일 수 있다. 페이지 트리 정렬은 MCP로 제어할 수 없으므로 사용자에게 알린다.

## 10. 매크로가 사이트에 없을 때

Page Properties, Roadmap Planner 같은 매크로는 타겟 사이트에 해당 기능이 없으면 깨진다. 플러그인 매크로는 더 그렇다.

**대응**: 소스에서 `data-extension-key`가 보이면 발행 전에 사용자에게 알리고, 깨질 경우 대체안(표·텍스트)을 제안한다.

## 11. 붙여넣기 결과가 0바이트

**증상**: 소스에서 copy 이벤트는 발생하는데 타겟 붙여넣기 후 문서 글자수 0, `clipboardData.types`가 빈 배열.

원인은 Chrome 창이 OS 포그라운드가 아닌 것(사용자가 다른 앱을 쓰는 중). 가상 textarea에 붙여도 비어 있다.

**대응**: JS `navigator.clipboard`로 우회하려 하지 않는다(렌더러가 45초 멈췄다). 사용자에게 "Chrome 창을 클릭해 앞으로 가져와 달라"고 요청한 뒤 같은 복사·붙여넣기를 재시도한다. 바로 복구됐다.

## 12. 탭 그룹 소실 — "This session's tab group no longer exists"

사용자가 (다른 PC의) 탭을 닫았거나, 브라우저를 둘 중 잘못 골랐을 때. 발행 전 초안은 남아 있다.

**대응**: 어느 브라우저인지 다시 묻고 `select_browser` → 새 그룹 → 초안 URL(`/pages/edit-v2/<id>`)을 열어 이어 쓴다. 처음부터 다시 하지 않는다.

## 13. 발행이 안 되고 edit-v2에 머무름

**증상**: '게시' 클릭 후 URL이 그대로. 좌하단 플래그 "페이지에 고유한 이름을 지정하세요".

Confluence는 **스페이스 전체** 제목 고유다. 다른 트리의 동명 페이지("타입 힌트")와 충돌한 것.

**대응**: 시작 전에 전 제목을 `/wiki/rest/api/content?spaceKey&title=`로 조회해 충돌 목록을 먼저 보고한다. 충돌 시 접미어(스킬명 등)를 제안해 사용자가 고르고, 제목 textarea를 클릭 → ctrl+a → 재입력한다. 완료 보고에 명시.

## 14. 게시 다이얼로그가 늦게 뜸

`[role=dialog]` 안 '게시' 버튼 대기 루프(최대 30초)가 가끔 'not found'로 끝난다. 스크린샷을 찍어 다이얼로그가 떠 있으면 버튼 좌표를 실클릭한다. JS `click()`이 안 먹을 때도 실클릭으로 해결됐다.

## 15. 첨부 REST 업로드 403 "XSRF check failed"

브라우저 세션에서 `POST /rest/api/content/{id}/child/attachment`는 `X-Atlassian-Token: no-check`·`atl_token` 어느 조합으로도 403. 페이지의 **첨부 파일 화면(`viewpageattachments.action`)의 폼**(`doattachfile.action`, 숨은 `atl_token`)으로 올리면 200. `clipboard-automation.md` §5.3.

## 16. 파일 매크로까지 덮어씀

`Invalid file id` 참조를 통째로 SVG 파일명으로 치환했더니 `.skill` 파일 매크로(`<ac:parameter>` 안의 `ri:attachment`)도 SVG를 가리키게 됐다. 정규식을 `<ac:image[^>]*>\s*<ri:attachment`로 한정하고, 파일 매크로는 원래 파일명으로 따로 연결한다.

## 17. 긴 코드블록이 잘린 것처럼 보임

74줄 코드블록이 에디터 DOM에서는 줄번호 31~ 만 보이고 `ENTRY`·`OPEN` 줄이 없었다. 가상 스크롤이다. `document.querySelector('.ProseMirror').pmViewDesc.node`의 `codeBlock` 노드 `textContent`로 세면 전부 있다. 검증은 항상 문서 모델로.

## 18. 소스가 폴더인데 descendants 404

`getConfluencePageDescendants`는 페이지 전용. 폴더는 `searchConfluenceUsingCql`의 `parent = <folderId> AND type = page`로 직계를 얻고, 타겟에도 **같은 이름 폴더를 먼저 만든다**. 폴더를 빼먹었다면 폴더 생성 후 `PUT /rest/api/content/{id}/move/append/{folderId}`로 12개 페이지를 옮겨 복구했다(자식은 따라온다, ID 불변).

## 19. 페이지 수를 잘못 셈

"41페이지"라 했는데 실제 40개였다. 보고 전 `/wiki/api/v2/pages/<루트>/descendants?limit=250&depth=5`의 `results.length`+1로 센다.
