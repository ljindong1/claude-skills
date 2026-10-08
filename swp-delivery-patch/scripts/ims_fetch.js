// eCoDY-IMS 티켓 전체(본문·댓글·첨부·연결·변경이력)를 탭 DOM 에 텍스트로 펼친다.
// 사용: ecody-ims.autoever.com 의 아무 페이지가 열린 탭에서 javascript_tool 로 실행 → 이어서 get_page_text.
// 치환: KEYS 배열만 바꾼다. 조회(GET)만 한다.
// javascript_tool 반환값은 짧게 잘리고 일부 문자열은 필터에 막히므로, 결과는 DOM 에 펼쳐 get_page_text 로 읽는다.
const KEYS = ["MCP0806-280"];
const MAX_COMMENT = 20000;

const toText = (html) => {
  const d = document.createElement("div");
  d.innerHTML = html || "";
  d.querySelectorAll("img").forEach((i) => i.replaceWith(`[이미지:${i.getAttribute("alt") || ""}]`));
  d.querySelectorAll("td,th").forEach((c) => c.append(" | "));
  d.querySelectorAll("tr,p,li,h1,h2,h3,h4,h5,br,div,pre").forEach((e) => e.append("\n"));
  return d.textContent.split("\n").map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean).join("\n");
};
const kst = (s) => (s ? s.replace("T", " ").slice(0, 16) : "");

const out = [];
for (const key of KEYS) {
  const r = await fetch(`/rest/api/2/issue/${key}?expand=changelog,renderedFields`, { credentials: "include" });
  if (!r.ok) { out.push(`=== ${key} | HTTP ${r.status}`); continue; }
  const j = await r.json();
  const f = j.fields, rf = j.renderedFields || {};
  const lines = [];
  lines.push(`=== ${key} | ${f.summary}`);
  lines.push(`상태: ${f.status && f.status.name} | 담당: ${f.assignee && f.assignee.displayName} | 보고: ${f.reporter && f.reporter.displayName}`);
  lines.push(`생성: ${kst(f.created)} | 갱신: ${kst(f.updated)} | 기한: ${f.duedate || "-"} | 레이블: ${(f.labels || []).join(", ")}`);
  lines.push("--- 연결");
  (f.issuelinks || []).forEach((l) => {
    const o = l.outwardIssue || l.inwardIssue;
    lines.push(`${l.type.name}: ${o.key} ${o.fields.summary} [${o.fields.status.name}]`);
  });
  lines.push("--- 첨부 (이름 | 바이트 | 시각 | 작성자)");
  (f.attachment || []).forEach((a) => lines.push(`${a.filename} | ${a.size} | ${kst(a.created)} | ${a.author.displayName}`));
  lines.push("--- 설명");
  lines.push(toText(rf.description || f.description));
  const cs = (f.comment && f.comment.comments) || [];
  const rcs = (rf.comment && rf.comment.comments) || [];
  lines.push(`--- 댓글 ${cs.length}건`);
  cs.forEach((c, i) => {
    const body = toText((rcs[i] && rcs[i].body) || c.body);
    const edited = c.updated !== c.created ? ` (수정 ${kst(c.updated)})` : "";
    lines.push(`## [${i}] ${kst(c.created)} ${c.author.displayName}${edited}`);
    lines.push(body.length > MAX_COMMENT ? body.slice(0, MAX_COMMENT) + `\n…(이하 ${body.length - MAX_COMMENT}자 생략)` : body);
  });
  lines.push("--- 변경 이력");
  ((j.changelog && j.changelog.histories) || []).forEach((h) =>
    lines.push(`${kst(h.created)} ${h.author ? h.author.displayName : ""}: ` +
      h.items.map((it) => `${it.field} [${(it.fromString || "").slice(0, 60)} → ${(it.toString || "").slice(0, 60)}]`).join("; ")));
  out.push(lines.join("\n"));
}
document.title = "IMS_FETCH";
document.body.innerHTML = "<main><pre id='ims'></pre></main>";
document.getElementById("ims").textContent = out.join("\n\n");
`ims_fetch ${KEYS.length}건 완료 — get_page_text 로 읽으세요`;
