// 수집 결과를 탭 DOM에 텍스트로 펼친다 → 이어서 get_page_text 로 한 번에 읽는다.
// (javascript_tool 반환값은 수천 자에서 잘리지만 get_page_text 는 긴 본문도 온전히 돌려준다)
// 형식: n|종류|id|그룹|하위분류|NEW/MOD/CMT|v|KST시각|작성자|제목|버전메시지|태그
const R = window.__ecm; if (!R) throw new Error("collect.js 를 먼저 실행");
const esc = s => String(s).replace(/[|\n]/g, " ");
const lines = R.rows.map(r => [r.n, r.k, r.id, r.g, r.sub, r.st, r.v, r.at, r.by, r.t, r.msg, r.tg].map(esc).join("|"));
const img = Object.entries(R.imgBy).map(([k, v]) => `IMG|${esc(k)}|${v}`);
document.title = "ECM_DUMP";
document.body.innerHTML = "<main><pre id='ecm'></pre></main>";
document.getElementById("ecm").textContent = ["#STATS " + JSON.stringify(R.stats), ...lines, ...img].join("\n");
`dumped ${lines.length} rows, ${img.length} image-containers`;
