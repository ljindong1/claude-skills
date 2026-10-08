// 선별한 eCoDY-IMS 이슈의 본문·댓글·첨부·연결·하위작업을 텍스트로 탭 DOM에 펼친다 → 이어서 get_page_text 로 읽는다.
// 사용: ecody-ims.autoever.com 의 아무 페이지가 열린 탭에서 javascript_tool 로 실행.
// 치환: __KEYS__ = ["CPINFO-4186","MCP0806-298"] (한 번에 5건 이하 권장), __MAX__ = 이슈당 최대 글자 수(기본 8000)
// [읽기 전용 가드] GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__imsGetOnly || (window.__imsGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const KEYS = __KEYS__; const MAX = __MAX__;
const toText = (html) => {
  const d = document.createElement("div"); d.innerHTML = html || "";
  d.querySelectorAll("img").forEach((i) => i.replaceWith(`[이미지:${i.getAttribute("alt") || ""}]`));
  d.querySelectorAll("td,th").forEach((c) => c.append(" | "));
  d.querySelectorAll("tr,p,li,h1,h2,h3,h4,h5,br,div,pre").forEach((e) => e.append("\n"));
  return d.textContent.split("\n").map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean).join("\n");
};
const day = (s) => (s ? s.replace("T", " ").slice(0, 16) : "");
const out = [];
for (const key of KEYS) {
  try {
    const r = await __get(`/rest/api/2/issue/${key}?expand=renderedFields`);
    if (!r.ok) { out.push(`=== ${key} | ERROR HTTP ${r.status}`); continue; }
    const j = await r.json(); const f = j.fields, rf = j.renderedFields || {};
    const L = [];
    L.push(`=== ${key} | ${f.summary}`);
    L.push(`유형: ${f.issuetype && f.issuetype.name} | 상태: ${f.status && f.status.name} | 보고: ${f.reporter ? f.reporter.displayName : ""} | 생성: ${day(f.created)} | 갱신: ${day(f.updated)}`);
    const links = (f.issuelinks || []).map((l) => { const o = l.outwardIssue || l.inwardIssue; return `${l.type.name}: ${o.key} ${o.fields.summary} [${o.fields.status.name}]`; });
    const subs = (f.subtasks || []).map((s) => `하위: ${s.key} ${s.fields.summary} [${s.fields.status.name}]`);
    if (f.parent) L.push(`상위: ${f.parent.key} ${f.parent.fields.summary}`);
    if (links.length || subs.length) L.push("--- 연결", ...links, ...subs);
    const att = (f.attachment || []).map((a) => `${a.filename} (${Math.round(a.size / 1024)}KB, ${day(a.created)})`);
    if (att.length) L.push("--- 첨부: " + att.join(", "));
    L.push("--- 설명", toText(rf.description || f.description));
    const cs = (f.comment && f.comment.comments) || [], rcs = (rf.comment && rf.comment.comments) || [];
    L.push(`--- 댓글 ${cs.length}건`);
    cs.forEach((c, i) => L.push(`## [${i}] ${day(c.created)} ${c.author.displayName}`, toText((rcs[i] && rcs[i].body) || c.body)));
    const text = L.join("\n");
    out.push(text.length > MAX ? text.slice(0, MAX) + `\n…(이하 ${text.length - MAX}자 생략)` : text);
  } catch (e) { out.push(`=== ${key} | ERROR ${e.message}`); }
}
document.title = "IMS_READ"; document.body.innerHTML = "<main><pre id='ims'></pre></main>";
document.getElementById("ims").textContent = out.join("\n\n");
`read ${KEYS.length} issues`;
