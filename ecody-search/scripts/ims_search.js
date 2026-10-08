// eCoDY-IMS 다중 JQL 검색 → 후보 병합 → 탭 DOM에 펼침 → 이어서 get_page_text 로 읽는다.
// 사용: ecody-ims.autoever.com 의 아무 페이지가 열린 탭에서 javascript_tool 로 실행.
// 치환: __QUERIES__ = [{tag:"Q1", jql:'text ~ "Os_Cfg"'}, ...] (최대 8개 권장)
// [읽기 전용 가드] GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__imsGetOnly || (window.__imsGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const QUERIES = __QUERIES__;
const PER_QUERY = 30;

const map = new Map(); const log = [];
for (const q of QUERIES) {
  try {
    const jql = /order by/i.test(q.jql) ? q.jql : q.jql + " ORDER BY updated DESC";
    const url = "/rest/api/2/search?jql=" + encodeURIComponent(jql) + `&maxResults=${PER_QUERY}` +
      "&fields=summary,project,status,issuetype,created,updated,reporter,comment";
    const r = await __get(url);
    if (!r.ok) { log.push(`${q.tag} HTTP ${r.status}`); continue; }
    const j = await r.json(); const res = j.issues || [];
    log.push(`${q.tag} ${res.length}/${j.total}건`);
    res.forEach((i, rank) => {
      const f = i.fields;
      const e = map.get(i.key) || { key: i.key, t: f.summary, prj: f.project.key, typ: f.issuetype && f.issuetype.name,
        st: f.status && f.status.name, cr: (f.created || "").slice(0, 10), up: (f.updated || "").slice(0, 10),
        rep: f.reporter ? f.reporter.displayName : "", nc: (f.comment && f.comment.total) || 0, hits: [], best: 999 };
      e.hits.push(q.tag); e.best = Math.min(e.best, rank); map.set(i.key, e);
    });
  } catch (err) { log.push(`${q.tag} ERROR ${err.message}`); }
}
const rows = [...map.values()].sort((a, b) => b.hits.length - a.hits.length || a.best - b.best);
const esc = s => String(s).replace(/[|\n]/g, " ");
const lines = rows.map((e, i) => [i + 1, e.key, e.prj, e.typ, e.st, e.cr, e.up, "댓글" + e.nc, e.hits.join("+"), e.rep, e.t].map(esc).join("|"));
window.__imsSearch = rows;
document.title = "IMS_SEARCH"; document.body.innerHTML = "<main><pre id='ims'></pre></main>";
document.getElementById("ims").textContent = ["#LOG " + log.join(" / "),
  "#FORMAT 순번|키|프로젝트|유형|상태|생성|갱신|댓글수|적중쿼리|보고자|제목", ...lines].join("\n");
`candidates ${rows.length}`;
