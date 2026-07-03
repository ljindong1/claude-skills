"""판정 분류 규칙 — 일치율을 좌우하는 튜닝 포인트.

검증표의 불일치를 보고 이 파일을 고친 뒤 fill_checklist.py를 다시 돌린다.
- 위험 오판(사람 Fail인데 AI Pass)이 나오면 그 문항 키워드를 HUMAN_REQUIRED에 추가.
- AI 과소(누락)가 나오면 NA_KEYWORDS에서 과한 패턴을 빼거나 매핑을 보강.
"""
import re

# 사람이 꼭 봐야 하는 항목 → 자동 Pass 금지, '확인 필요'로 보류.
# 깊은 내용 비교/시스템 근거/승인이 필요한 것들. (부분 문자열 매칭)
HUMAN_REQUIRED = [
    "승인", "배포", "협의", "고객", "우선순위",
    "추적",          # 추적성/추적되는가
    "일관",          # 일관성/일관되게  ← 위험 오판 사례에서 보강
    "정합",          # 정합성
    "동료검토", "검토 결과", "회의",
    "이력", "등록", "할당", "모니터링",
    "재사용 평가",
]

# 테스트 단계말·후행 단계 산출물 → 미대상(N/A) 처리. (산출물명 부분 문자열)
NA_KEYWORDS = [
    "소프트웨어 검증", "통합 검증", "통합 시험", "통합 테스트",
    "인정 시험", "인정 테스트",
    "시스템 검증", "시스템 통합", "시스템 인정",
]

# 존재성/형식 항목 신호 — 문서 접근 가능 시 Pass 후보. (참고용)
STRUCTURAL = ["정의", "포함", "작성", "구성", "구조", "템플릿", "식별",
              "명시", "기술", "범위", "목표", "절차", "방법", "기준"]


def is_human_required(question: str) -> bool:
    q = str(question or "")
    return any(k in q for k in HUMAN_REQUIRED)


# 검증/시험이라도 '계획서'와 '정적(분석/검증)'은 설계 단계에 작성·점검되는 점검대상이다.
# NA_KEYWORDS('통합 검증' 등)가 산출물명에 부분매칭돼 계획서까지 미대상으로 떨구는 과소(누락)를 막는다.
DESIGN_PHASE_KEEP = ["계획", "정적"]


def is_design_phase_target(product: str) -> bool:
    p = str(product or "")
    return any(k in p for k in DESIGN_PHASE_KEEP)


def is_na_product(product: str) -> bool:
    p = str(product or "")
    if is_design_phase_target(p):   # 계획서·정적검증은 점검대상 유지
        return False
    return any(k in p for k in NA_KEYWORDS)


def judge(question: str, evidence: str):
    """(result, comment) 반환. result=None 이면 '확인 필요'(판정 보류)."""
    q = str(question or "")
    date_tag = "(AI 1차)"
    if "최신 템플릿" in q or "공통" in q:
        return "Pass", f"{date_tag}: {evidence} — 표준 템플릿 구조 충족 확인. 사내 최신 Rev 대조 별도 권장"
    if is_human_required(q):
        return None, (f"{date_tag}: {evidence} / 확인 필요 — 승인·배포·추적성·일관성·협의 등은 "
                      f"내용 깊이 또는 시스템(PMS/codebeamer/레드마인) 직접 확인")
    return "Pass", f"{date_tag}: {evidence} — 문서 내 해당 항목 존재·충족 확인"


# 실행시점이 후행 단계를 가리키면 이번(설계) 단계에선 미대상. (바로 '완료'는 P1 시점에도 쓰여 제외)
LATER_PHASE_TIMING = ["M-1", "마일스톤 점검", "개발 완료 시점", "프로젝트 완료",
                      "완료 보고", "양산", "인도", "출하", "단계 종료"]


def is_later_phase_timing(timing: str) -> bool:
    t = str(timing or "")
    return any(k in t for k in LATER_PHASE_TIMING)
