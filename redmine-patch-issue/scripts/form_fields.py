#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""등록 폼의 필수 표시와 허용값 전체를 뽑는다.

Redmine REST API 로는 "필수 여부" 와 "목록형 필드의 전체 허용값" 을 알 수 없다(관리자 전용).
대신 **이슈 조회 화면 HTML 에 수정 폼이 함께 들어 있다** — 거기에
`제목 *` 같은 필수 표시와 `<select>` 의 option 전체가 그대로 있다.

`/issues/new` 는 API 키 Basic 인증으로 열리지 않는다(302 -> /login).
그래서 **같은 프로젝트·같은 추적의 기존 일감 번호**를 하나 준다.

    python -I form_fields.py 49949
    python -I form_fields.py 49949 --out C:\\path\\fields.txt

환경변수: REDMINE_URL · REDMINE_API_KEY
"""
import argparse
import base64
import html
import io
import os
import re
import sys
import urllib.request


def fetch(url: str, key: str) -> str:
    req = urllib.request.Request(url)
    token = base64.b64encode(f"{key}:x".encode()).decode()
    req.add_header("Authorization", "Basic " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def report(page: str, issue_id: str) -> str:
    out = io.StringIO()
    w = out.write

    w(f"# 일감 #{issue_id} 등록 폼\n\n")
    hits = {k: len(re.findall(k, page)) for k in ("common_mark", "textile")}
    w(f"본문 서식기 흔적: common_mark {hits['common_mark']} 회 · "
      f"textile {hits['textile']} 회 — 많은 쪽이 켜진 서식기다.\n")
    w("  (확정 확인은 이 일감 화면에서 본문의 `## 머리말` 이 h2 로 렌더됐는지 보는 것이다)\n\n")

    m = re.search(r'<form[^>]*action="/issues/\d+"[^>]*>(.*?)</form>', page, re.S)
    if not m:
        w("⚠ 수정 폼이 없다 — 이 일감을 수정할 권한이 없거나 화면 구조가 바뀌었다.\n")
        return out.getvalue()
    seg = m.group(1)

    w("## 필드와 필수 여부  (★ = 필수)\n\n")
    for lm in re.finditer(r'<label[^>]*for="([^"]+)"[^>]*>(.*?)</label>', seg, re.S):
        fid = lm.group(1)
        txt = html.unescape(re.sub("<[^>]+>", "", lm.group(2))).strip()
        req = "★" if txt.endswith("*") else " "
        w(f"  {req} {fid:42s} {txt}\n")

    w("\n## 목록형 필드의 허용값 전체\n")
    for sm in re.finditer(r'<select[^>]*id="([^"]+)"[^>]*>(.*?)</select>', seg, re.S):
        sid, body = sm.group(1), sm.group(2)
        vals = re.findall(r'<option[^>]*value="([^"]*)"', body)
        texts = [
            html.unescape(re.sub("<[^>]+>", "", o)).strip()
            for o in re.findall(r"<option[^>]*>.*?</option>", body, re.S)
        ]
        w(f"\n  {sid}  ({len(vals)} 개)\n")
        for v, t in zip(vals, texts):
            mark = "  -- 구분선, 값이 아니다" if re.fullmatch(r"[=\s]*[^=]*[=\s]*", t) and t.count("=") >= 4 else ""
            w(f"      {v!r:>12} = {t}{mark}\n")

    w("\n## 입력형 필드의 현재 값\n")
    for im in re.finditer(r'<input[^>]*id="(issue_[^"]+)"[^>]*>', seg):
        tag = im.group(0)
        t = re.search(r'type="([^"]+)"', tag)
        v = re.search(r'value="([^"]*)"', tag)
        w(f"  {im.group(1):42s} type={t.group(1) if t else '?':9s} "
          f"value={html.unescape(v.group(1)) if v else ''!r}\n")

    w("\n※ 사용자정의 필드는 **추적마다 다르다.** 같은 추적의 일감으로 확인한다.\n")
    return out.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("issue", help="같은 프로젝트·같은 추적의 기존 일감 번호")
    ap.add_argument("--out", help="결과를 쓸 파일 (기본: 표준출력)")
    a = ap.parse_args()

    base = (os.environ.get("REDMINE_URL") or "").rstrip("/")
    key = os.environ.get("REDMINE_API_KEY") or ""
    if not base or not key:
        print("REDMINE_URL · REDMINE_API_KEY 가 필요하다.", file=sys.stderr)
        return 1

    try:
        page = fetch(f"{base}/issues/{a.issue}", key)
    except Exception as e:  # noqa: BLE001
        print(f"조회 실패: {e}", file=sys.stderr)
        print("사내망인지, 일감 번호가 맞는지 확인한다.", file=sys.stderr)
        return 1

    text = report(page, a.issue)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {a.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
