// eCoDY-ECM 변경 수집기 — javascript_tool 로 ecody-ecm.autoever.com 탭에서 실행
// 사용: 아래 CFG 두 값만 치환해서 실행한다. (UTC ISO 문자열)
// [읽기 전용 가드] 이 스크립트는 GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__ecmGetOnly || (window.__ecmGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const CFG = { windowStartUtc: "__WINDOW_START_UTC__", windowEndUtc: "__WINDOW_END_UTC__" };

const ws = new Date(CFG.windowStartUtc), we = new Date(CFG.windowEndUtc);
if (isNaN(ws) || isNaN(we)) throw new Error("CFG 날짜 치환 누락");
const pad = n => String(n).padStart(2, "0");
// CQL 날짜는 서버 시간대로 해석되므로 하루 앞당겨 넉넉히 받고, version.when(UTC)으로 정밀 필터한다.
const lb = new Date(ws.getTime() - 24 * 3600e3);
const since = `${lb.getUTCFullYear()}/${pad(lb.getUTCMonth() + 1)}/${pad(lb.getUTCDate())} 00:00`;

async function sweep(type, expand) {
  let url = "/rest/api/content/search?cql=" + encodeURIComponent(`lastmodified >= "${since}" and type=${type}`) + `&limit=100&expand=${expand}`;
  const out = []; let guard = 0;
  while (url && guard++ < 100) {
    const r = await __get(new URL(url, location.origin), { credentials: "include" });
    if (!r.ok) throw new Error(`${type} HTTP ${r.status}`);
    const j = await r.json();
    out.push(...(j.results || []));
    url = (j._links && j._links.next && (j.results || []).length) ? j._links.next : null;
  }
  return out;
}

const ROOTS = [
  ["Integration Auditor Guide", "IA"], ["Validation Checker Guide", "VC"], ["Validation checker로", "VC"],
  ["Notice", "NOTICE"], ["Policy", "POLICY"],
  ["IM (Integration Manual)", "IM"], ["SAG (SW Application Guide)", "SAG"],
  ["Autosar Module User Manual", "UM"], ["C Studio Manual", "CSTUDIO"],
];
function classify(spaceKey, ancTitles) {
  if (spaceKey !== "mclassicfaq") return { g: "OTHER", sub: spaceKey };
  for (const [needle, code] of ROOTS) {
    const i = ancTitles.findIndex(t => (needle === "Notice" || needle === "Policy") ? t === needle : t.includes(needle));
    if (i >= 0) return { g: code, sub: (ancTitles[i + 1] || "").slice(0, 30) };
  }
  return { g: "MISC", sub: (ancTitles[1] || "").slice(0, 30) };
}
function tags(title) {
  const t = [];
  const r = title.match(/\b(R4[04X]|R4x)\b/i); if (r) t.push(r[1].toUpperCase());
  const m = title.match(/\b(CYT\w*|TC[23]\w*|S32K\w*|S32G\w*|SPC58\w*|F1KM?[\w-]*|U2A\w*|RCAR\w*|U5L|RH850\w*)/i); if (m) t.push(m[1]);
  const mod = title.match(/^\s*(?:\[[^\]]*\]\s*)*?\[([A-Za-z][A-Za-z0-9_]{1,15})\]/) || title.match(/^([A-Za-z][A-Za-z0-9_]{1,15}) - \d/);
  if (mod && !/^(R4|IA|VC|SAG|TASK|Patch|Package|FEATURE|V\.C)/i.test(mod[1])) t.push(mod[1]);
  return t.join(",");
}
const inWin = iso => { const d = new Date(iso); return d > ws && d <= we; };
const kst = iso => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(5, 16).replace("T", " ");

const [pages, blogs, comments, atts] = await Promise.all([
  sweep("page", "version,history,space,ancestors"),
  sweep("blogpost", "version,history,space,ancestors"),
  sweep("comment", "version,space,container,container.ancestors"),
  sweep("attachment", "version,space,container,container.ancestors"),
]);

const rows = []; const imgBy = {}; let imgCount = 0;
for (const p of [...pages, ...blogs]) {
  if (!inWin(p.version.when)) continue;
  const c = classify(p.space.key, p.ancestors.map(a => a.title));
  rows.push({ k: p.type === "page" ? "P" : "B", id: p.id, g: c.g, sub: c.sub,
    st: new Date(p.history.createdDate) > ws ? "NEW" : "MOD", v: p.version.number, at: kst(p.version.when),
    by: p.version.by.displayName, t: p.title, msg: (p.version.message || "").slice(0, 60), tg: tags(p.title) });
}
for (const x of comments) {
  if (!inWin(x.version.when)) continue;
  const ct = x.container || {}; const c = classify(x.space.key, [...(ct.ancestors || []).map(a => a.title), ct.title || ""]);
  rows.push({ k: "C", id: ct.id, g: c.g, sub: c.sub, st: "CMT", v: x.version.number, at: kst(x.version.when),
    by: x.version.by.displayName, t: ct.title || "", msg: "", tg: tags(ct.title || "") });
}
for (const a of atts) {
  if (!inWin(a.version.when)) continue;
  const ct = a.container || {};
  if (/\.(png|jpe?g|gif|bmp|svg|webp)$/i.test(a.title)) { imgCount++; imgBy[ct.title || "?"] = (imgBy[ct.title || "?"] || 0) + 1; continue; }
  const c = classify(a.space.key, [...(ct.ancestors || []).map(q => q.title), ct.title || ""]);
  rows.push({ k: "A", id: ct.id, g: c.g, sub: c.sub, st: a.version.number === 1 ? "NEW" : "MOD", v: a.version.number,
    at: kst(a.version.when), by: a.version.by.displayName, t: `${a.title} @ ${ct.title || ""}`, msg: "", tg: tags(ct.title || "") });
}
const ORDER = ["NOTICE", "POLICY", "IA", "VC", "SAG", "IM", "UM", "CSTUDIO", "OTHER", "MISC"];
rows.sort((a, b) => ORDER.indexOf(a.g) - ORDER.indexOf(b.g) || (a.st === "NEW" ? -1 : 1) - (b.st === "NEW" ? -1 : 1) || b.at.localeCompare(a.at));
rows.forEach((r, i) => r.n = i + 1);
const stats = { window: [CFG.windowStartUtc, CFG.windowEndUtc], raw: { page: pages.length, blog: blogs.length, comment: comments.length, attachment: atts.length },
  rows: rows.length, imgExcluded: imgCount, byGroup: {} };
for (const r of rows) { const s = stats.byGroup[r.g] ||= { NEW: 0, MOD: 0, CMT: 0, total: 0 }; s[r.st]++; s.total++; }
window.__ecm = { rows, stats, imgBy };
JSON.stringify(stats);
