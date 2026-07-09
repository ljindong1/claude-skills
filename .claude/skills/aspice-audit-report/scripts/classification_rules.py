"""판정 분류 규칙 — 1차 스코핑·힌트 제공(판정 아님).

[evidence 브리핑 재정의, references/roadmap.md]
judge()는 더 이상 Pass를 자동 부여하지 않는다. Pass는 오직 본문 정독 계층
(comment_style.md 형식의 comments.json)에서 실제 산출물의 Intent 충족 근거를
'인용'했을 때만 부여된다. 이 파일의 역할은 (a) 스코핑(미대상/조건부/후행단계)과
(b) '무엇을 어디서 확인해야 하는지' 힌트를 주는 것으로 한정된다.
- 구 버전의 structural 키워드 자동 Pass('문서 내 해당 항목 존재·충족 확인')는 제거했다
  — 근거 없는 일반 문구 Pass가 위험 오판의 주원인이었다.
- HUMAN_REQUIRED는 이제 '자동 확인필요 고정'이 아니라 '본문/대체 산출물/시스템 중
  어디를 봐야 하는지'를 알려주는 힌트 축이다. 대체 근거로 Pass 인정 여부는
  comment_style.md(대체 근거 규칙)가 정하며 judge()는 관여하지 않는다.
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
# "설계서/아키텍처/설계 명세"는 설계 단계말의 핵심 점검대상 — NA 키워드 부분매칭에서 보호
# (실측: CN8 No.32 시스템 아키텍처 설계서가 미대상으로 오분류된 과소 사례 수정)
DESIGN_PHASE_KEEP = ["계획", "정적", "설계서", "아키텍처", "설계 명세", "단위"]


def is_design_phase_target(product: str) -> bool:
    p = str(product or "")
    return any(k in p for k in DESIGN_PHASE_KEEP)


def is_na_product(product: str) -> bool:
    p = str(product or "")
    if is_design_phase_target(p):   # 계획서·정적검증은 점검대상 유지
        return False
    return any(k in p for k in NA_KEYWORDS)


def judge(question: str, evidence: str):
    """(result, comment) 반환. 항상 result=None(확인 필요/보류) — 판정은 정독 계층 몫.

    Pass는 이 함수가 아니라 본문 정독(comments.json)에서 근거 인용과 함께 부여된다.
    여기서는 '어떤 Intent를, 어디서(표준 위치→없으면 대체 산출물/회의록/다른 활동),
    무엇을 인용해 판정해야 하는지'만 힌트로 남긴다.
    """
    q = str(question or "")
    date_tag = "(AI 1차)"
    if is_human_required(q):
        return None, (f"{date_tag}: 확인 필요 — {evidence}. "
                      f"승인·배포·추적성·일관성·협의 등 Intent는 산출물 본문(및 표준 위치에 없으면 "
                      f"대체 산출물·회의록·다른 활동)에서 직접 정독하거나 시스템 확인 후 판정. "
                      f"Pass는 근거(파일·절·활동) 인용 필수, 아니면 읽어야 할 산출물을 지목")
    return None, (f"{date_tag}: 확인 필요 — {evidence}. "
                  f"해당 Intent 충족 여부를 산출물 본문에서 직접 정독 후 판정"
                  f"(표준 위치에 없으면 대체 산출물·회의록·다른 활동 근거 탐색). "
                  f"Pass는 근거 인용 필수, 아니면 읽어야 할 산출물을 지목")


# 실행시점이 후행 단계를 가리키면 이번(설계) 단계에선 미대상. (바로 '완료'는 P1 시점에도 쓰여 제외)
LATER_PHASE_TIMING = ["M-1", "마일스톤 점검", "개발 완료 시점", "프로젝트 완료",
                      "완료 보고", "양산", "인도", "출하", "단계 종료"]


def is_later_phase_timing(timing: str) -> bool:
    t = str(timing or "")
    return any(k in t for k in LATER_PHASE_TIMING)


# 조건부 활동: 실행시점이 "주기 도래/발생 시"류면 발생 여부를 폴더로 알 수 없다.
# (실측: 형상감사·CCB 등 27건 과대 스코핑의 주원인 — 사람은 '미도래→No', AI는 일괄 Yes)
CONDITIONAL_TRIGGERS = ["도래", "발생 시", "발생시"]


def is_conditional_activity(timing: str) -> bool:
    t = str(timing or "")
    return any(k in t for k in CONDITIONAL_TRIGGERS)


# 사건발생형 활동: 실행시점이 빈칸이라도 활동 자체가 '사건이 있어야' 수행되는 것들.
# (실측: CN8 과대 27건 중 25건이 실행시점 빈칸 — 형상감사·CCB·변경요청 발생류)
# 폴더에 수행 흔적(출력 산출물)이 있으면 발생한 것이므로 보류하지 않는다 — fill에서 hit 우선.
# 주의: 문제해결/레드마인 상시 절차는 사람이 Yes로 보는 항목이 많아 여기 넣지 않는다.
EVENT_DRIVEN = ["형상감사", "형상 감사", "CCB", "변경 요청 관리", "변경요청 관리", "변경 발생"]


def is_event_driven(output_product: str, question: str = "") -> bool:
    t = str(output_product or "") + " " + str(question or "")
    return any(k in t for k in EVENT_DRIVEN)


# 상시 운영 활동: 시스템(레드마인/PMS) 근거라도 모든 단계에서 점검대상(Yes)이다.
# (실측: 2차 CN8에서 이들을 "P1 범위 밖" 일괄 미대상 처리 → 과소 12건 전원 이 유형)
ONGOING_ACTIVITIES = ["문제 해결", "문제해결", "이슈 관리", "이슈관리", "레드마인",
                      "모니터링", "의사소통", "이슈"]


def is_ongoing_activity(output_product: str, question: str = "") -> bool:
    t = str(output_product or "") + " " + str(question or "")
    return any(k in t for k in ONGOING_ACTIVITIES)
