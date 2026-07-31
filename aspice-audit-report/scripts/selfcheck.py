#!/usr/bin/env python3
"""스킬 스크립트 무결성 자가진단 — 오디트 시작 시 가장 먼저 실행한다.

배경(실측): 일부 실행 환경에서 스킬 파일이 VM 마운트에 '잘린 스냅샷'으로 보이는
문제가 관찰됐다(config.py가 1,545바이트/35줄로 줄 중간에서 끊김, stat 크기도 잘린 값,
cp로 복사해도 그대로. 최근 갱신된 파일일수록 발생 경향). 이 상태로 스크립트를 돌리면
SyntaxError 또는 조용한 오동작이 난다.

usage:
  python selfcheck.py            # 이 파일이 있는 scripts/ 폴더를 검사
  python selfcheck.py <폴더>     # 지정 폴더 검사

[FAIL]이 나오면:
1) 각 스크립트를 Read 툴(호스트 경로)로 전체를 읽어, 쓰기 가능한 작업 폴더에 온전한
   사본으로 Write해 복원하고, 이후 그 사본(PYTHONPATH)으로 워크플로를 실행한다.
2) 복원한 파일을 Edit로 고치면 마운트가 다시 잘린 뷰를 줄 수 있다 — 수정은 반드시
   '새 파일명'으로 새로 쓴다(새 inode는 항상 신선하게 읽힘).
3) 사용자에게 스킬 재설치(Save skill) 또는 세션 재시작을 권고한다.
"""
import os
import sys
import json
import time
import py_compile

# 파일별 '끝부분 존재' 센티널 — 잘림은 컴파일이 통과해도 뒷부분이 없을 수 있다
SENTINELS = {
    "config.py": "def clear_cols",
    "classification_rules.py": "def is_ongoing_activity",
    "fill_checklist.py": 'ap.add_argument("--sheet"',
    "verify_comment_coverage.py": "sys.exit(main(",
    "make_blank_template.py": "a.new_sheet, a.copy_from",
    "write_comments.py": "main(a.result, a.comments, a.sheet)",
    "verify_against_baseline.py": "main(a.ai, a.human, a.out, a.sheet)",
    "build_comparison.py": "main(a.result, a.human, a.out, a.sheet)",
    "check_contamination.py": "sys.exit(main(a.ai, a.human, a.sheet))",
    "template_version.py": "sys.exit(main())",
    "build_mapping_report.py": "if __name__",
    "adopt_template.py": "다음 단계: .skill 재패키징",
    "repair_padded_xlsx.py": "sys.exit(repair(",
}


def check_once(folder):
    bad = []
    for fn in sorted(os.listdir(folder)):
        path = os.path.join(folder, fn)
        if not os.path.isfile(path):
            continue
        try:
            if fn.endswith(".py"):
                py_compile.compile(path, doraise=True)
                sent = SENTINELS.get(fn)
                if sent:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        if sent not in f.read():
                            bad.append((fn, f"끝부분 센티널 없음({sent!r}) — 잘림 의심"))
            elif fn.endswith(".json"):
                json.load(open(path, encoding="utf-8"))
        except Exception as e:
            bad.append((fn, f"{type(e).__name__}: {str(e)[:60]}"))
    return bad


def main(folder, retries=3, wait_s=10):
    """실패 시 대기 후 재시도 — 세션 초기 파일 동기화가 끝나기 전이면 자가 회복된다."""
    for attempt in range(1, retries + 1):
        bad = check_once(folder)
        if not bad:
            tag = "" if attempt == 1 else f" (재시도 {attempt - 1}회 후 동기화 회복됨)"
            print(f"[OK] {folder} 스크립트·JSON 전체 무결 — 그대로 진행{tag}")
            return 0
        if attempt < retries:
            print(f"[재시도 {attempt}/{retries - 1}] 무결성 이상 {len(bad)}건 — 동기화 지연 가능성, {wait_s}초 대기 후 재검사…")
            time.sleep(wait_s)
    print(f"[FAIL] 스킬 파일 무결성 이상 {len(bad)}건 — 재시도 후에도 지속(마운트 스냅샷 잘림):")
    for fn, why in bad:
        print(f"  {fn}: {why}")
    print("→ 조치: 각 파일을 Read 툴(호스트 경로)로 읽어 작업 폴더에 복원 후 그 사본으로 실행.")
    print("  복원본 수정은 Edit가 아니라 '새 파일명' Write로. 양식 xlsx는 사용자에게 원본 첨부 요청.")
    return 1


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    sys.exit(main(d))
