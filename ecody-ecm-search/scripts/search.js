// eCoDY-ECM 다중 CQL 검색 → 후보 병합·분류 → 탭 DOM에 펼침 → 이어서 get_page_text 로 읽는다.
// 치환: __QUERIES__ = [{tag:"T1", cql:'space=mclassicfaq and title ~ "Wdg" and type=page'}, ...] (최대 8개 권장)
// [읽기 전용 가드] 이 스크립트는 GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__ecmGetOnly || (window.__ecmGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const QUERIES = __QUERIES__;
const PER_QUERY = 25;

const ROOTS = [
  ["Integration Auditor Guide", "IA"], ["Validation Checker Guide", "VC"], ["Validation checker로", "VC"],
  ["Notice", "NOTICE"], ["Policy", "POLICY"],
  ["IM (Integration Manual)", "IM"], ["SAG (SW Application Guide)", "SAG"],
  ["Autosar Module User Manual", "UM"], ["C Studio Manual", "CSTUDIO"],
];
function classify(spaceKey, anc) {
  if (spaceKey !== "mclassicfaq") return { g: "OTHER", sub: spaceKey };
  for (const [needle, code] of ROOTS) {
    const i = anc.findIndex(t => (needle === "Notice" || needle === "Policy") ? t === needle : t.includes(needle));
    if (i >= 0) return { g: code, sub: (anc[i + 1] || "").slice(0, 30) };
  }
  return { g: "MISC", sub: (anc[1] || "").slice(0, 30) };
}
const kstDate = iso => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(0, 10);
const map = new Map(); const log = [];
for (const q of QUERIES) {
  try {
    const url = "/rest/api/content/search?cql=" + encodeURIComponent(q.cql) + `&limit=${PER_QUERY}&expand=space,ancestors,version`;
    const r = await __get(url, { credentials: "include" });
    if (!r.ok) { log.push(`${q.tag} HTTP ${r.status}`); continue; }
    const j = await r.json(); const res = j.results || [];
    log.push(`${q.tag} ${res.length}건`);
    res.forEach((p, rank) => {
      const e = map.get(p.id) || { id: p.id, t: p.title, sp: p.space.key, ...classify(p.space.key, (p.ancestors || []).map(a => a.title)),
        upd: kstDate(p.version.when), v: p.version.number, hits: [], best: 999 };
      e.hits.push(q.tag); e.best = Math.min(e.best, rank); map.set(p.id, e);
    });
  } catch (err) { log.push(`${q.tag} ERROR ${err.message}`); }
}
const rows = [...map.values()].sort((a, b) => b.hits.length - a.hits.length || a.best - b.best);
const esc = s => String(s).replace(/[|\n]/g, " ");
const lines = rows.map((e, i) => [i + 1, e.id, e.g, e.sub, e.upd, "v" + e.v, e.hits.join("+"), e.t].map(esc).join("|"));
window.__ecmSearch = rows;
document.title = "ECM_SEARCH"; document.body.innerHTML = "<main><pre id='ecm'></pre></main>";
document.getElementById("ecm").textContent = ["#LOG " + log.join(" / "), "#FORMAT 순번|pageId|그룹|하위분류|최종수정(KST)|버전|적중쿼리|제목", ...lines].join("\n");
`candidates ${rows.length}`;
