#!/usr/bin/env python3
"""Jenkins 빌드가 끝날 때까지 기다리고, 콘솔 로그를 저장하고, 빌드 검수 요약을 낸다.

환경변수: JENKINS_URL, JENKINS_USER, JENKINS_TOKEN (사내 인증서 검증 생략)
사용:
  python jenkins_wait.py <job> [<번호>|last] [--compare <빌드 번호>] [--log <저장 경로>] [--timeout 3600]
  --compare: 직전 회차의 '전체 재생성' 빌드 번호. 증분 빌드와 비교하면 Generate 정보가 없어 의미 없다.
오래 걸리므로 Claude Code 에서는 Bash run_in_background 로 실행하고 완료 알림을 기다린다.

읽을 때 주의 — 아래 셋은 서로 다른 말이다.
  * ERR 0건 + Validation 수행 모듈 0개  = 미수행. 통과가 아니다
  * ERR 0건 + 수행 모듈에 내 모듈 없음  = 그 모듈은 미수행 (증분 빌드가 건너뜀)
  * ERR 0건 + 수행 모듈에 내 모듈 있음  = 통과
빌드 결과가 SUCCESS 라도 UTIP 이 실패해 .s19 가 안 나올 수 있다(훅이 성패에 반영하지 않는다).
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
    # Toolset 3.0.3 은 숫자를 <0> 처럼 꺾쇠로 감싼다. 맨숫자 형식도 함께 받는다
    gen = re.findall(r"INF000004: <?(\d+)>? Error\(s\) and <?(\d+)>? Warning", text)
    # 생성기 실행 횟수와 그때 넘긴 모듈 목록 — 증분이면 일부 모듈만 들어간다
    mods = re.findall(r"mobilgene_c_generator\.exe\s.*?\s-M\s+([A-Za-z0-9_ ]+?)\s+-T\s", text)
    runs = len(re.findall(r"mobilgene_c_generator\.exe\s", text))
    val = re.findall(r"\[(\w+)\] Validation (SUCCESS|FAILED|FAIL)", text)
    rte = re.findall(r"Rte Validation Finished\. (\d+) errors, (\d+) warnings", text)
    saf = collections.Counter(re.findall(r"(SAFERTE_(?:WARN|ERR)_\d+)", text))
    errs = re.findall(r"\bERR\d{5,6}\b", text)          # ERR0 으로 시작하지 않는 코드도 잡는다
    wrns = collections.Counter(re.findall(r"\bWRN\d{5,6}\b", text))
    arts = re.findall(r"Making binary\(([^)]+)\)", text) + re.findall(r"\[PostPackage\] Built artifact\s*:\s*(\S+)", text)
    target = re.findall(r"JENKINS_BUILD_TARGET\s*:\s*(\w+)", text)
    hook = re.findall(r"\[HOOK\] ([\w ]+?) ERROR LEVEL\s*:\s*(\d+)", text)
    return {
        "gen_errors": sum(int(e) for e, _ in gen), "gen_warnings": sum(int(w) for _, w in gen),
        "gen_runs": runs, "gen_modules": sorted({m for g in mods for m in g.split()}),
        "val_ok": sorted({m for m, r in val if r == "SUCCESS"}),
        "val_bad": sorted({m for m, r in val if r != "SUCCESS"}),
        "rte": [(int(e), int(w)) for e, w in rte],
        "saferte_err": sum(v for k, v in saf.items() if "_ERR_" in k), "saferte": dict(saf),
        "validation_err_codes": sorted(set(errs)), "warn_codes": dict(wrns.most_common()),
        "artifacts": sorted(set(arts)), "target": target[:1],
        "utip_ok": len(re.findall(r"UTIP_SUCCESS", text)), "utip_fail": len(re.findall(r"UTIP_FAIL", text)),
        "hook": hook, "no_new_elf": "No new .elf file" in text,
    }


def report(s, head):
    print(head)
    print(f"   생성기: 실행 {s['gen_runs']}회, Error {s['gen_errors']} / Warning {s['gen_warnings']}")
    if s["gen_modules"]:
        print(f"   생성 모듈 {len(s['gen_modules'])}개: {' '.join(s['gen_modules'])}")
    elif s["gen_runs"] == 0:
        print("   ⚠ 생성기 실행 기록 없음 — 생성 단계가 돌지 않았다")
    print(f"   Validation 수행 {len(s['val_ok'])}개 / 실패 {len(s['val_bad'])}개")
    if s["val_ok"]:
        print(f"      수행: {' '.join(s['val_ok'])}")
    if s["val_bad"]:
        print(f"      ⚠ 실패: {' '.join(s['val_bad'])}")
    if not s["val_ok"]:
        print("   ⚠ Validation 이 한 모듈도 돌지 않았다 — ERR 0건을 '통과'로 읽지 마라 (미수행)")
    print(f"   Validation 오류 코드: {s['validation_err_codes'] or '없음'}"
          + ("" if s["val_ok"] else "  ← 미수행 상태의 0건"))
    print(f"   경고 코드: {s['warn_codes'] or '없음'}")
    print(f"   Rte Validation: {s['rte']}  SAFERTE_ERR {s['saferte_err']}")
    mark = "  ⚠ UTIP 실패 — .s19 가 만들어지지 않았다" if s["utip_fail"] else ""
    print(f"   UTIP: 성공 {s['utip_ok']} / 실패 {s['utip_fail']}{mark}")
    if s["hook"]:
        print("   훅 ERROR LEVEL: " + ", ".join(f"{k.strip()}={v}" for k, v in s["hook"]))
    if s["no_new_elf"]:
        print("   ⚠ 'No new .elf file' — 훅이 실패로 처리하고 Git Push 를 건너뛴다")
    print(f"   산출물: {s['artifacts']}")


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
    report(s, f"== {a.job} #{num}: {d['result'] or '진행 중(시간 초과)'}  {d['duration'] // 1000}s  target={s['target']}")
    if a.compare:
        b = summarize(get(f"/job/{a.job}/{a.compare}/consoleText").decode("utf-8", "replace"))
        report(b, f"== 비교 #{a.compare}")
        if b["gen_runs"] == 0:
            print("   ⚠ 비교 빌드에 Generate 기록이 없음 — 직전 회차의 전체 재생성 빌드를 고르세요")
        print(f"== 대조: Rte {'같음' if b['rte'] == s['rte'] else '다름'}")
        only_now = sorted(set(s["val_ok"]) - set(b["val_ok"]))
        only_cmp = sorted(set(b["val_ok"]) - set(s["val_ok"]))
        print(f"   Validation 수행 모듈 차이: 이번만 {only_now or '없음'} / 비교만 {only_cmp or '없음'}")
        diff = {k: (b["saferte"].get(k, 0), s["saferte"].get(k, 0)) for k in set(b["saferte"]) | set(s["saferte"]) if b["saferte"].get(k, 0) != s["saferte"].get(k, 0)}
        print(f"   SAFERTE 종류별 증감: {diff or '없음'}")


if __name__ == "__main__":
    main()
