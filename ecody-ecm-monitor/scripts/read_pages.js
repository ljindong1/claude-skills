// 지정 페이지의 본문(body) 또는 "수집 구간 시작 시점 버전 → 현재" 변경 줄(diff)을 탭 DOM에 펼친다.
// 이어서 get_page_text 로 읽는다. (javascript_tool 반환값은 수천 자에서 잘린다)
// 치환: __WINDOW_START_UTC__ (collect.js 와 같은 값), __JOBS__ (예: [{id:"380196632",mode:"body"},{id:"319465743",mode:"diff"}])
// [읽기 전용 가드] 이 스크립트는 GET 조회만 한다. GET 이외 요청이 섞이면 즉시 중단한다.
const __get = window.__ecmGetOnly || (window.__ecmGetOnly = (u, o = {}) => {
  if (o.method && o.method.toUpperCase() !== "GET") throw new Error("읽기 전용 스킬: GET 이외 요청 금지");
  return fetch(u, { ...o, method: "GET", credentials: "include" });
});
const WINDOW_START = new Date("__WINDOW_START_UTC__");
const JOBS = __JOBS__;
const MAX = 2500; // 페이지당 출력 상한(자). 요약용이므로 앞부분이면 충분하다.

const toText = html => { const d = document.createElement("div"); d.innerHTML = html;
  d.querySelectorAll("td,th").forEach(c => c.append(" | "));
  d.querySelectorAll("tr,p,li,h1,h2,h3,h4,h5,br,div,pre").forEach(e => e.append("\n"));
  return d.textContent.split("\n").map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean); };
async function j(url) { const r = await __get(url, { credentials: "include" }); if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`); return r.json(); }
const content = (id, ver) => j(`/rest/api/content/${id}${ver ? `?status=historical&version=${ver}&` : "?"}expand=body.view,version`);
async function baseVersion(id) { // 구간 시작 시각 이전의 마지막 버전 번호 (없으면 null = 구간 내 신규)
  for (let start = 0; start < 2000; start += 50) {
    const v = await j(`/rest/experimental/content/${id}/version?limit=50&start=${start}`);
    const hit = (v.results || []).find(x => new Date(x.when) <= WINDOW_START);
    if (hit) return hit.number;
    if (!v.results || v.results.length < 50) return null;
  }
  return null;
}
const out = [];
for (const job of JOBS) {
  try {
    const cur = await content(job.id); const curL = toText(cur.body.view.value);
    let head = `=== ${job.id} | ${cur.title} | v${cur.version.number}`, text;
    const base = job.mode === "diff" ? await baseVersion(job.id) : null;
    if (job.mode === "diff" && base && base !== cur.version.number) {
      const prevL = toText((await content(job.id, base)).body.view.value);
      const ps = new Set(prevL), cs = new Set(curL);
      const add = curL.filter(l => !ps.has(l)).map(l => "+ " + l), del = prevL.filter(l => !cs.has(l)).map(l => "- " + l);
      head += ` | diff v${base}→v${cur.version.number}`;
      text = (add.length || del.length) ? [...add, ...del].join("\n") : "(텍스트 변화 없음 — 서식·첨부만 변경)";
    } else {
      if (job.mode === "diff") head += " | 구간 내 신규 → 본문";
      text = curL.join("\n");
    }
    out.push(`${head}\n${text.slice(0, MAX)}${text.length > MAX ? "\n…(이하 생략)" : ""}`);
  } catch (e) { out.push(`=== ${job.id} | ERROR ${e.message}`); }
}
document.title = "ECM_READ"; document.body.innerHTML = "<main><pre id='ecm'></pre></main>";
document.getElementById("ecm").textContent = out.join("\n\n");
`read ${JOBS.length} pages`;
