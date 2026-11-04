// eCoDY-ECM 다중 CQL 검색 → 후보 병합·분류 → 탭 DOM에 펼침 → 이어서 get_page_text 로 읽는다.
// 치환: __QUERIES__ = [{tag:"T1", cql:'space=mclassicfaq and title ~ "Wdg" and type=page'}, ...] (최대 8개 권장)
// [읽기 전용 가드] 이 스크립트는 GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__ecmGetOnly || (window.__ecmGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const QUERIES = __QUERIES__;
const PER_QUERY = 25;

// 2026-11-04 실측 트리(mclassicfaq 최상위): 📢 Notice / 🏁 Terms of Use (ToU) /
// 🔧 Technical Reference(1️⃣ IM, 2️⃣ SAG) / 📝Autosar Module User Manual /
// 📚mobilgene Tool Manual / ✅ Quality & Verification / 파일 목록.
// 제목에 이모지·번호 접두사가 붙어 있어 비교 전에 앞쪽 비문자를 떼어 낸다(ecm_api.py 와 같은 표).
const ROOTS = [
  ["Integration Auditor Guide", "IA"],
  ["Validation Checker Guide", "VC"], ["Validation checker", "VC"], ["필수 통합 점검", "VC"],
  ["IM (Integration Manual)", "IM"],
  ["SAG (", "SAG"],
  ["Notice", "NOTICE"],
  ["Policy", "POLICY"], ["Quality & Verification", "POLICY"],
  ["Terms of Use", "ToU"],
  ["Autosar Module User Manual", "UM"],
  ["C Studio", "CSTUDIO"], ["mobilgene Tool Manual", "CSTUDIO"],
];
const norm = t => String(t || "").replace(/^[^0-9A-Za-z가-힣[(]+/, "").trim();
function classify(spaceKey, anc) {
  if (spaceKey !== "mclassicfaq") return { g: "OTHER", sub: spaceKey };
  const titles = anc.map(norm);
  for (const [needle, code] of ROOTS) {
    const i = titles.findIndex(t => (needle === "Notice" || needle === "Policy") ? t === needle : t.includes(needle));
    if (i >= 0) return { g: code, sub: (titles[i + 1] || "").slice(0, 30) };
  }
  return { g: "MISC", sub: (titles[0] || "").slice(0, 30) };
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
