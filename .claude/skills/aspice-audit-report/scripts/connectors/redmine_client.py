#!/usr/bin/env python3
"""레드마인 REST API 클라이언트 (사내망 실행 전용).

문제해결 관리 절차 점검과 부적합 ID 연계를 위해 이슈 데이터를 끌어온다.
샌드박스에서는 사내망에 닿지 않으므로, 반드시 사내망 PC에서 실행할 것.
엔드포인트·커스텀필드 ID는 레드마인 버전/설정마다 다를 수 있으니 인스턴스에서 검증하라.

설정: connectors_config.json (connectors_config.example.json 참고) 또는 환경변수
  REDMINE_URL, REDMINE_API_KEY  (환경변수가 설정 파일보다 우선)

usage:
  python redmine_client.py --summary --project swrc_cn8
  python redmine_client.py --issue 43641
  python redmine_client.py --summary --project swrc_cn8 --out redmine_evidence.json
"""
import os
import sys
import json
import argparse
import urllib.parse

try:
    import requests
except ImportError:
    sys.exit("requests 필요: pip install requests")


def load_config(path="connectors_config.json"):
    url = os.environ.get("REDMINE_URL")
    key = os.environ.get("REDMINE_API_KEY")
    cfg = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f).get("redmine", {})
    return {
        "url": url or cfg.get("url"),
        "api_key": key or cfg.get("api_key"),
        "verify_ssl": cfg.get("verify_ssl", True),
        "default_project_id": cfg.get("default_project_id"),
    }


class Redmine:
    def __init__(self, url, api_key, verify_ssl=True, timeout=15):
        if not url or not api_key:
            raise ValueError("REDMINE_URL / REDMINE_API_KEY 가 필요합니다 (설정 또는 환경변수).")
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.verify = verify_ssl
        self.s = requests.Session()
        # 헤더 인증이 ?key= 보다 로그에 안 남아 안전하다.
        self.s.headers.update({"X-Redmine-API-Key": api_key,
                               "Content-Type": "application/json"})
        if not verify_ssl:
            import warnings
            warnings.warn("verify_ssl=False — 사내 자체서명 인증서 환경에서만 사용하세요.")

    def _get(self, path, params=None):
        r = self.s.get(f"{self.url}/{path}", params=params or {},
                       timeout=self.timeout, verify=self.verify)
        r.raise_for_status()
        return r.json()

    def issue(self, iid):
        """부적합 ID 검증용 — 이슈 1건의 상태·제목·tracker 반환(없으면 None)."""
        try:
            j = self._get(f"issues/{iid}.json")["issue"]
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise
        return {"id": j["id"], "subject": j.get("subject"),
                "status": j.get("status", {}).get("name"),
                "tracker": j.get("tracker", {}).get("name"),
                "updated_on": j.get("updated_on")}

    def issues(self, project_id=None, extra=None):
        """프로젝트의 모든 이슈(열림+닫힘)를 페이지네이션으로 수집."""
        out, offset, limit = [], 0, 100
        while True:
            params = {"status_id": "*", "limit": limit, "offset": offset}
            if project_id:
                params["project_id"] = project_id
            if extra:
                params.update(extra)
            j = self._get("issues.json", params)
            out.extend(j.get("issues", []))
            total = j.get("total_count", 0)
            offset += limit
            if offset >= total or not j.get("issues"):
                break
        return out

    def summary(self, project_id=None):
        """tracker·status 분포 집계 — 문제해결 관리 점검 근거."""
        issues = self.issues(project_id)
        by_tracker, by_status = {}, {}
        for it in issues:
            t = it.get("tracker", {}).get("name", "?")
            st = it.get("status", {}).get("name", "?")
            by_tracker[t] = by_tracker.get(t, 0) + 1
            by_status[st] = by_status.get(st, 0) + 1
        return {"project": project_id, "total": len(issues),
                "by_tracker": by_tracker, "by_status": by_status,
                "issue_ids": [it["id"] for it in issues]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="connectors_config.json")
    ap.add_argument("--project", default=None)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--issue", type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    c = load_config(a.config)
    rm = Redmine(c["url"], c["api_key"], c["verify_ssl"])
    project = a.project or c["default_project_id"]
    result = {}
    if a.issue is not None:
        result["issue"] = rm.issue(a.issue)
        print(json.dumps(result["issue"], ensure_ascii=False, indent=2))
    if a.summary:
        result["summary"] = rm.summary(project)
        s = result["summary"]
        print(f"[레드마인 요약] project={s['project']} total={s['total']}")
        print("  tracker:", s["by_tracker"])
        print("  status :", s["by_status"])
    if a.out and result:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("저장:", a.out)


if __name__ == "__main__":
    main()
