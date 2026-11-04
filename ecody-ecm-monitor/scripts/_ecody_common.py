#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ecm_monitor.py 공용 부품 — 토큰·GET·HTML→텍스트·출력.

ecody-search/scripts/_ecody_common.py 와 같은 파일이다(스킬을 따로 설치해도 돌게 복사본을 둔다).
한쪽을 고치면 다른 쪽도 같이 고친다.

[읽기 전용 가드] get() 은 GET 요청만 만든다. 다른 메서드를 넣을 수단을 두지 않는다.
토큰·URL 환경변수 (SITE 는 IMS 또는 ECM):
  ECODY_<SITE>_TOKEN   개인 액세스 토큰 (필수)
  ECODY_<SITE>_URL     기본값 https://ecody-<site>.autoever.com
  ECODY_<SITE>_INSECURE=1 / ECODY_<SITE>_NOPROXY=1   인증서·프록시 우회
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

DEFAULT_URL = {"IMS": "https://ecody-ims.autoever.com", "ECM": "https://ecody-ecm.autoever.com"}


class Site:
    """한 사이트(IMS·ECM)의 접속 설정과 GET 호출."""

    def __init__(self, name):
        self.name = name.upper()
        self.url = (os.environ.get(f"ECODY_{self.name}_URL") or DEFAULT_URL[self.name]).rstrip("/")
        self.token, self.source = self._token()

    def _token(self):
        var = f"ECODY_{self.name}_TOKEN"
        t = (os.environ.get(var) or "").strip()
        if t:
            return t, f"환경변수 {var}"
        raise SystemExit(
            f"TOKEN_MISSING: 환경변수 {var} 이 비어 있다.\n"
            f'  등록: setx {var} "<eCoDY-{self.name} 개인 액세스 토큰>"  (발급 절차는 references/api-token.md)\n'
            "  이미 떠 있는 세션에서 쓰려면 명령 앞에\n"
            f"    $env:{var}=[Environment]::GetEnvironmentVariable('{var}','User');\n"
            "  를 붙인다.\n"
            "토큰 없이 진행하려면 기존 크롬 방식(scripts/*_search.js)으로 돌아간다."
        )

    def _opener(self):
        handlers = []
        if os.environ.get(f"ECODY_{self.name}_INSECURE") == "1":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        if os.environ.get(f"ECODY_{self.name}_NOPROXY") == "1":
            handlers.append(urllib.request.ProxyHandler({}))
        return urllib.request.build_opener(*handlers)

    def get(self, path):
        """GET 전용. path 는 /rest/... 형태. (본문, HTTP 코드) 를 돌려준다."""
        req = urllib.request.Request(self.url + path, method="GET")
        if req.get_method() != "GET":  # 읽기 전용 가드
            raise RuntimeError("읽기 전용 스킬: GET 이외 요청 금지")
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Accept", "application/json")
        try:
            with self._opener().open(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8", "replace")), r.status
        except urllib.error.HTTPError as e:
            return {"__error": f"HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}"}, e.code
        except Exception as e:  # DNS·TLS·프록시 등
            return {"__error": f"{type(e).__name__} {e}"}, 0


class _Text(HTMLParser):
    BLOCK = {"tr", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "div", "pre", "table", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.buf.append("[이미지:{}]".format(dict(attrs).get("alt") or ""))
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.buf.append(" | ")
        elif tag in self.BLOCK:
            self.buf.append("\n")

    def handle_data(self, data):
        self.buf.append(data)


def to_text(html):
    """Confluence body.view / Jira renderedFields 의 HTML 을 읽기 좋은 평문으로."""
    if not html:
        return ""
    p = _Text()
    p.feed(str(html))
    p.close()
    lines = [" ".join(s.split()).strip() for s in "".join(p.buf).split("\n")]
    return "\n".join(s for s in lines if s)


def day(s):
    """ISO 시각 → 'YYYY-MM-DD HH:MM' (Jira 응답은 이미 KST 오프셋이 붙어 온다)."""
    return s.replace("T", " ")[:16] if s else ""


def kst_date(iso):
    """UTC(Z) 시각 → KST 날짜 'YYYY-MM-DD' (Confluence version.when 용)."""
    import datetime as _dt
    if not iso:
        return ""
    s = iso.replace("Z", "+00:00")
    try:
        t = _dt.datetime.fromisoformat(s)
    except ValueError:
        return iso[:10]
    if t.tzinfo is None:
        t = t.replace(tzinfo=_dt.timezone.utc)
    return (t.astimezone(_dt.timezone(_dt.timedelta(hours=9)))).strftime("%Y-%m-%d")


def esc(s):
    """파이프 표 한 칸에 넣을 값 — 구분자·줄바꿈 제거."""
    return str(s if s is not None else "").replace("|", " ").replace("\n", " ")


def clip(text, limit):
    return text if len(text) <= limit else text[:limit] + f"\n…(이하 {len(text) - limit}자 생략)"


def load_queries(path, key):
    """[{"tag","cql"|"jql"}] JSON 파일 → [(tag, 쿼리문)]"""
    with open(path, "r", encoding="utf-8-sig") as f:
        qs = json.load(f)
    return [(q.get("tag") or f"Q{n}", q[key]) for n, q in enumerate(qs, 1)]


def emit(text, out):
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"WROTE {out} ({len(text)}자)")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
