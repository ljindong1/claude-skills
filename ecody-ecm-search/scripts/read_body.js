// 선별한 페이지의 본문을 텍스트로 탭 DOM에 펼친다 → 이어서 get_page_text 로 읽는다.
// 치환: __IDS__ = ["202544012","334015765"]  (한 번에 5건 이하 권장), __MAX__ = 페이지당 최대 글자 수(기본 6000)
// [읽기 전용 가드] 이 스크립트는 GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__ecmGetOnly || (window.__ecmGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const IDS = __IDS__; const MAX = __MAX__;
const toText = html => { const d = document.createElement("div"); d.innerHTML = html;
  d.querySelectorAll("td,th").forEach(c => c.append(" | "));
  d.querySelectorAll("tr,p,li,h1,h2,h3,h4,h5,br,div,pre").forEach(e => e.append("\n"));
  return d.textContent.split("\n").map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean).join("\n"); };
const out = [];
for (const id of IDS) {
  try {
    const r = await __get(`/rest/api/content/${id}?expand=body.view,version,ancestors,children.attachment`, { credentials: "include" });
    if (!r.ok) { out.push(`=== ${id} | ERROR HTTP ${r.status}`); continue; }
    const p = await r.json(); const text = toText(p.body.view.value);
    const att = (p.children?.attachment?.results || []).map(a => a.title).filter(t => !/\.(png|jpe?g|gif|bmp|svg)$/i.test(t));
    const when = new Date(new Date(p.version.when).getTime() + 9 * 3600e3).toISOString().slice(0, 10);
    out.push(`=== ${id} | ${p.title} | v${p.version.number} | ${when} | ${p.version.by.displayName}\n경로: ${p.ancestors.map(a => a.title).slice(1).join(" > ")}\n문서첨부: ${att.join(", ") || "-"}\n${text.slice(0, MAX)}${text.length > MAX ? `\n…(이하 ${text.length - MAX}자 생략)` : ""}`);
  } catch (e) { out.push(`=== ${id} | ERROR ${e.message}`); }
}
document.title = "ECM_READ"; document.body.innerHTML = "<main><pre id='ecm'></pre></main>";
document.getElementById("ecm").textContent = out.join("\n\n");
`read ${IDS.length} pages`;
