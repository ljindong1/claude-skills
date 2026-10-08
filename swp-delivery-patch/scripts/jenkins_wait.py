#!/usr/bin/env python3
"""Jenkins 빌드가 끝날 때까지 기다리고, 콘솔 로그를 저장하고, 빌드 검수 요약을 낸다.

환경변수: JENKINS_URL, JENKINS_USER, JENKINS_TOKEN (사내 인증서 검증 생략)
사용:
  python jenkins_wait.py <job> [<번호>|last] [--compare <빌드 번호>] [--log <저장 경로>] [--timeout 3600]
  --compare: 직전 회차의 '전체 재생성' 빌드 번호. 증분 빌드와 비교하면 Generate 정보가 없어 의미 없다.
오래 걸리므로 Claude Code 에서는 Bash run_in_background 로 실행하고 완료 알림을 기다린다.
"""
import argparse, base64, collections, io, json, os, re, ssl, sys, time, urllib.error, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def client():
    u = os.environ.get("JENKINS_URL", "").rstrip("/")
    user, tok = os.environ.get("JENKINS_USER"), os.environ.get("JENKINS_TOKEN")
    if not (u and user and tok):
        sys.exit("JENKINS_URL / JENKINS_USER / JENKINS_TOKEN 환경변수가 필요합니다 (setx 로 등록).")
    auth = base64.b64encode(f"{user}:{tok}".encode()).decode()
    ctx = ssl._create_unverified_context()

    def get(path):
        req = urllib.request.Request(u + path, headers={"Authorization": "Basic " + auth})
        return urllib.request.urlopen(req, context=ctx, timeout=120).read()
    return get


def summarize(text):
    gen = re.findall(r"INF000004: (\d+) Error\(s\) and (\d+) Warning", text)
    rte = re.findall(r"Rte Validation Finished\. (\d+) errors, (\d+) warnings", text)
    saf = collections.Counter(re.findall(r"(SAFERTE_(?:WARN|ERR)_\d+)", text))
    errs = re.findall(r"\bERR0\d{5}\b", text)
    arts = re.findall(r"Making binary\(([^)]+)\)", text) + re.findall(r"\[PostPackage\] Built artifact\s*:\s*(\S+)", text)
    target = re.findall(r"JENKINS_BUILD_TARGET\s*:\s*(\w+)", text)
    return {
        "gen_errors": sum(int(e) for e, _ in gen), "gen_warnings": sum(int(w) for _, w in gen), "gen_runs": len(gen),
        "rte": [(int(e), int(w)) for e, w in rte],
        "saferte_err": sum(v for k, v in saf.items() if "_ERR_" in k), "saferte": dict(saf),
        "validation_err_codes": sorted(set(errs)), "artifacts": sorted(set(arts)), "target": target[:1],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("num", nargs="?", default="last")
    ap.add_argument("--compare")
    ap.add_argument("--log")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    get = client()
    num = a.num
    if num == "last":
        num = str(json.loads(get(f"/job/{a.job}/api/json?tree=lastBuild[number]"))["lastBuild"]["number"])
    t0 = time.time()
    while True:
        try:
            d = json.loads(get(f"/job/{a.job}/{num}/api/json?tree=building,result,duration,timestamp"))
        except urllib.error.HTTPError as e:
            # push 직후에는 빌드가 아직 대기열(quiet period)에 있어 번호가 404 — 시작될 때까지 기다린다
            if e.code != 404 or time.time() - t0 > a.timeout:
                raise
            time.sleep(30)
            continue
        if not d["building"] or time.time() - t0 > a.timeout:
            break
        time.sleep(30)
    text = get(f"/job/{a.job}/{num}/consoleText").decode("utf-8", "replace")
    if a.log:
        open(a.log, "w", encoding="utf-8").write(text)
    s = summarize(text)
    print(f"== {a.job} #{num}: {d['result'] or '진행 중(시간 초과)'}  {d['duration'] // 1000}s  target={s['target']}")
    print(f"   생성기: Error {s['gen_errors']} / Warning {s['gen_warnings']} (실행 {s['gen_runs']}회 — 0회면 증분 빌드)")
    print(f"   Rte Validation: {s['rte']}  SAFERTE_ERR {s['saferte_err']}")
    print(f"   Validation 오류 코드: {s['validation_err_codes'] or '없음'}")
    print(f"   산출물: {s['artifacts']}")
    if a.compare:
        b = summarize(get(f"/job/{a.job}/{a.compare}/consoleText").decode("utf-8", "replace"))
        print(f"== 비교 #{a.compare}: 생성기 Error {b['gen_errors']} / Warning {b['gen_warnings']}, Rte {b['rte']}, SAFERTE_ERR {b['saferte_err']}")
        if b["gen_runs"] == 0:
            print("   ⚠ 비교 빌드에 Generate 기록이 없음 — 직전 회차의 전체 재생성 빌드를 고르세요")
        print(f"   Rte Validation {'같음' if b['rte'] == s['rte'] else '다름'}")
        diff = {k: (b["saferte"].get(k, 0), s["saferte"].get(k, 0)) for k in set(b["saferte"]) | set(s["saferte"]) if b["saferte"].get(k, 0) != s["saferte"].get(k, 0)}
        print(f"   SAFERTE 종류별 증감: {diff or '없음'}")


if __name__ == "__main__":
    main()
