# claude-skills

Claude 커스텀 스킬 모음이자 형상관리 저장소.

정본은 **Claude 계정에 등록된 스킬**이고, 이 저장소는 그 이력을 남기는 사본이다. 방향은 항상 `계정 → 저장소` 한 방향이다. 저장소에서 파일을 고쳐도 계정 스킬은 바뀌지 않는다.

## 저장소 구조

스킬 폴더가 **저장소 최상위**에 바로 놓인다.

```
skills-repo/
├── README.md
├── setup-script.sh                     # 클라우드 환경 부팅 시 스킬 설치용
├── arxml-analyzer/
│   ├── SKILL.md
│   ├── references/                     # 개념 설명·용어집·예시
│   └── scripts/                        # ARXML 검사·변환
├── aspice-audit-mapping/
│   ├── SKILL.md
│   ├── assets/                         # 대시보드 템플릿·mapping 스키마·OII 맵·Target 시트 양식
│   ├── references/                     # 매칭 규칙·출력 계약
│   └── scripts/                        # Target 시트 파싱·산출물 스캔·매핑·검증
├── aspice-audit-report/
│   ├── SKILL.md
│   ├── assets/                         # 체크리스트 템플릿(.xlsx)
│   ├── references/
│   ├── scripts/                        # 매핑·판정·검증
│   └── *.example.json                  # deliverable_map·intent_map 예시
├── autosar-artifact-map/
│   ├── SKILL.md
│   ├── references/                     # mobilgene Classic 스택 규칙
│   └── scripts/                        # 4단계 스캔 파이프라인
├── can-bench-setup/
│   ├── SKILL.md
│   ├── assets/                         # 벤치 readme 템플릿
│   ├── projects/                       # 차종별 벤치 설정·측정 trace
│   ├── references/                     # Joule·CANoe 사용법, 트러블슈팅
│   └── scripts/                        # python-can(pycan)·CANoe 호출, 프로젝트 정보 수집
├── confluence-cross-site-copy/
│   ├── SKILL.md
│   └── references/                     # 경로 판정, 클립보드 자동화·첨부 복원, storage→HTML 변환, 함정
├── confluence-project-page/
│   ├── SKILL.md
│   ├── assets/                         # 페이지 본문 HTML 템플릿
│   └── references/
├── confluence-writing/
│   ├── SKILL.md
│   └── references/
├── cvd-project/
│   └── SKILL.md                        # 절차만 - 라이팅 도구·설정은 Joule 저장소 (joule-flash)
├── daily-standup/
│   └── SKILL.md
├── ecody-ecm-monitor/
│   ├── SKILL.md
│   ├── references/                     # 원장·당일 기록 페이지 형식, 사내 Confluence 수정 절차
│   ├── scripts/                        # eCoDY 변경분 수집·본문 덤프 (크롬 연동)
│   └── run.cmd · setup-task.ps1        # 작업 스케줄러 무인 실행 등록
├── ecody-ims-patch-monitor/
│   ├── SKILL.md
│   ├── references/                     # 정리 페이지 규격(꼬리표)·수집 범위 가이드
│   └── run.cmd · setup-task.ps1        # 작업 스케줄러 무인 실행 등록
├── ecody-search/
│   ├── SKILL.md
│   ├── references/                     # ECM CQL·IMS JQL 쿼리 설계 가이드
│   └── scripts/                        # ECM·IMS 검색·본문 읽기 (읽기 전용)
├── gitea-jenkins-setup/
│   ├── SKILL.md
│   ├── assets/                         # 표준 배치 파일(CRLF)·Jenkins Job XML 템플릿
│   ├── references/                     # 토큰 발급·Chrome 모드·트러블슈팅
│   └── scripts/                        # Fork·공동작업자·클론·Job 생성 CLI
├── gwantongsa-mock-exam/
│   ├── SKILL.md
│   ├── references/                     # 국사·관광자원 출제 규칙, 최신화 체크리스트
│   └── scripts/                        # 시험지 검증·인쇄용 PDF 빌드
├── hota/
│   └── SKILL.md                        # 절차만 - 도구·프로필·문서는 Joule 저장소 (joule-hota)
├── joule-repo-sync/
│   ├── SKILL.md
│   └── scripts/                        # 회사 Gitea → 개인 GitHub 미러링, 주간 작업 등록
├── redmine-daily-dashboard/
│   ├── SKILL.md
│   ├── references/                     # 대시보드 HTML 형식 정본
│   ├── scripts/                        # 수집·델타 산출·조각 렌더링
│   └── run.cmd · setup-task.ps1        # 작업 스케줄러 무인 실행 등록
├── redmine-issue/
│   ├── SKILL.md
│   └── scripts/                        # Redmine REST 조회 CLI (읽기 전용)
├── redmine-patch-issue/
│   ├── SKILL.md
│   ├── references/                     # 본문 골격·절별 규격, 완성 본문 예시, 사내 등록 양식 근거
│   │   └── projects/                   # 제어기별 확정 필드값·상시 시험
│   └── scripts/                        # 등록 폼 HTML 에서 필수 필드·허용값 추출
├── skill-repo-sync/
│   ├── SKILL.md
│   └── scripts/                        # 계정 → 저장소 미러링
├── slack-morning-briefing/
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── sources.json                    # 감시 대상 채널·DM 목록
├── slack-to-calendar/
│   └── SKILL.md
├── svg-creation/
│   ├── SKILL.md
│   └── references/                     # 패턴·아이콘 라이브러리
├── swp-delivery-patch/
│   ├── SKILL.md
│   ├── evals/                          # 평가 프롬프트·채점 기준
│   ├── references/                     # 3-way 판정·IMS·버전업·Jenkins·검증·양식·판단 규칙, projects/ 프로젝트 프로필
│   └── scripts/                        # 배포본 CRC 대조·3-way 판정·당사 수정 탐지·심볼 점검·빌드/생성물/메모리 검수
├── tech-research-to-confluence/
│   ├── SKILL.md
│   └── references/
├── travel-english-weekly/
│   ├── SKILL.md
│   └── references/                     # 표현 라이브러리
├── watchdog/                           # 스킬 아님 - 예약 실행 점검 PowerShell (register_task.ps1 · check_runs.ps1)
└── synced/                             # git 제외 - Claude Code 스킬 동기화가 쓰는 자리 (지우지 않는다)
```

스킬 이름은 파일명이 아니라 **폴더명**으로 정해진다. 각 스킬은 자기 폴더 안에 `SKILL.md` 를 두고, 보조 자료가 있으면 같은 폴더에 함께 둔다.

> **`.claude/` 폴더를 저장소 안에 만들지 말 것.** Claude 데스크탑 앱은 `.claude/skills` 경로를 보호 대상으로 취급해서, 그 경로를 품은 폴더는 **저장소도 상위 폴더도 전부 마운트를 거부**한다. 이 저장소가 예전 `claude-skills` 에서 옮겨온 이유가 그것이다.

## 세 곳의 관계

```
계정 스킬 (Claude 앱에서 편집하는 정본)
    │  세션 시작 시 사본이 내려옴
    ▼
Claude 세션의 읽기 전용 스냅샷
    │  skill-repo-sync 스킬이 복사
    ▼
D:\Ljindong\skills-repo/                 ← 이 저장소
    ▲
    │  디렉터리 정션
C:\Users\ljindong\.claude\skills/        ← VS Code(Claude Code)가 읽는 곳
```

`C:\Users\ljindong\.claude\skills` 는 이 저장소를 가리키는 **정션(바로가기)** 이다. 저장소를 갱신하면 VS Code 쪽도 자동으로 같이 바뀐다. 따로 복사할 필요가 없다.

정션이 살아있는지 확인:

```powershell
(Get-Item C:\Users\ljindong\.claude\skills).LinkType   # Junction 이면 정상
```

다시 걸어야 하면:

```powershell
Remove-Item -Recurse -Force C:\Users\ljindong\.claude\skills
New-Item -ItemType Junction -Path C:\Users\ljindong\.claude\skills -Target D:\Ljindong\skills-repo
```

## 저장소 갱신하는 법

앱에서 스킬을 고친 뒤 Claude(Cowork)에게 말하면 된다.

```
<스킬명> 스킬을 저장소에 반영해줘
```

`skill-repo-sync` 스킬이 계정 스냅샷과 저장소를 비교해 파일을 복사한다. 커밋·푸시는 사용자가 실행한다 — Claude 샌드박스는 `.git/index.lock` 을 지우지 못하고 푸시 인증도 없기 때문이다.

```powershell
cd D:\Ljindong\skills-repo
Remove-Item .git\index.lock -Force -ErrorAction SilentlyContinue
git add -A
git status --short
git commit -m "<스킬명>: 계정 최신본 반영"
git push
```

주의할 점 두 가지.

- **스킬을 고친 그 대화에서 바로 요청하지 말 것.** 계정 스냅샷은 대화 시작 시점에 한 번 내려오므로 수정 전 버전이 반영될 수 있다. 새 대화에서 요청하는 편이 안전하다.
- **스킬 이름을 지정할 것.** 이름 없이 전체를 요청하면 저장소에 일부러 두지 않은 스킬까지 들어온다.

수동으로 하려면 스크립트를 직접 돌려도 된다.

```bash
python3 skill-repo-sync/scripts/sync_skills.py \
  --repo <저장소 경로> --source <계정 스킬 폴더> --skills <스킬명> --dry-run
```

## 클라우드 환경에 설치

클라우드 세션은 매번 빈 컨테이너로 초기화되어 스킬을 영구 저장할 수 없다. 세션 시작 시 실행되는 설정 스크립트에서 이 저장소를 받아 설치한다.

1. `setup-script.sh` 의 `REPO_URL` 을 이 저장소 주소로 바꾼다.
2. 그 내용을 클라우드 환경 설정의 **"설정 스크립트"** 칸에 붙여넣는다.
3. 실행하면 로그에 `[설치 완료] 스킬 N개:` 와 목록이 나온다.

스크립트는 저장소 최상위에서 `SKILL.md` 를 가진 폴더만 골라 설치하므로 `README.md` 나 자기 자신은 자동으로 제외된다. 스킬을 추가해도 스크립트는 고칠 필요가 없다.

## 스킬 목록

| 스킬 | 용도 |
| --- | --- |
| `arxml-analyzer` | AUTOSAR ARXML 구조를 개념 중심으로 정리해 Confluence 에 보고 |
| `aspice-audit-mapping` | ASPICE 오디트 1단계 — 체크리스트 Target 시트와 산출물 폴더를 대조·매핑하고 HTML 대시보드로 시각화 |
| `aspice-audit-report` | ASPICE 품질점검 체크리스트를 자동 1차 작성하고 사람 작성본과 대비해 일치율 측정·개선 |
| `autosar-artifact-map` | AUTOSAR 프로젝트 폴더를 4단계 스캔해 BSWMD → ECUC → 코드 → 모듈 의존의 산출물 추적성 지도 생성 |
| `can-bench-setup` | 실험대 ECU 가 CAN DB 대로 보내는지 Joule 로 확인 — 레스트버스 깨우기, 주기·길이·FD·카운터·CRC 대조, 슬립, 자극→응답 심화 TC, 새 빌드 전체 평가. `canoe` 모드는 차종 컨피그 추출·현행 DB 갱신·검증 |
| `confluence-cross-site-copy` | 서로 다른 Confluence 사이트 간에 페이지·폴더 트리를 복사 (MCP/브라우저 경로 판정, 클립보드 자동화로 서식·SVG·PNG 첨부까지 복원) |
| `confluence-project-page` | mobaseasec Confluence 에 신규 프로젝트 페이지 세트를 표준 템플릿으로 생성 |
| `confluence-writing` | Confluence 글쓰기 톤·구조·서식과 MCP 발행 규약의 정본 |
| `cvd-project` | CVD(CodeViser) 과제 단위로 빌드 결과를 CLI 로 MCU 에 기록하고 이미지와 대조 검증. 프로젝트 폴더를 조사해 모르는 것만 묻고, 스킬 동봉 기본 틀로 생성 (쓰기는 매번 확인 후, S32_Config 무참조) |
| `daily-standup` | 슬랙 데일리 스탠드업을 대화로 작성해 본인 이름으로 게시 |
| `ecody-ecm-monitor` | eCoDY-ECM 변경분을 매일 수집해 그룹별 누적 원장과 날짜별 기록으로 사내 Confluence 에 발행 |
| `ecody-ims-patch-monitor` | eCoDY-IMS Delivery_Patch 티켓 하나에서 출발해 연결된 자료 전부(짝 패치, 수평전개 원본·사본, 중간 버전 릴리즈 노트와 하위작업, ECM 의 IM·IA/VC·SAG)를 긁어모아 사내 Confluence 정리 페이지(대표 1장 + 부록)로 갱신 (읽기 전용, 페이지는 지우지 않고 본문만 교체) |
| `ecody-search` | eCoDY-ECM(가이드)·eCoDY-IMS(릴리즈 노트·수평전개·문의) 를 CQL/JQL 다중 검색·정독해 근거 링크와 함께 답변 (읽기 전용, 구 ecody-ecm-search) |
| `gitea-jenkins-setup` | 사내 Gitea 저장소를 Fork해 공동작업자·작업 브랜치·표준 배치 파일·Jenkins Job(비활성)까지 자동 빌드 환경을 한 번에 구축 (생성 전용) |
| `gwantongsa-mock-exam` | 관광통역안내사 필기 모의고사(국사 25 + 관광자원해설 25)를 이력 기반 중복 방지·사실 검증을 거쳐 생성하고 인쇄용 2단 PDF로 전달 |
| `hota` | H-OTA A·B 그룹 리프로그래밍 평가(1세대 External·BG→Repro / 2세대 Wired·Wireless·Rule Units)를 Joule `joule-hota` 로 — 서명본 hash 판별(재빌드 감지), 보드 준비, Report Config·OEUK 준비, .log 정리·자동 판정, 이름 규칙 검사·수정, 보드평가레포트·Redmine zip·결과 표 (보드 쓰기·외부 등록은 승인 후) |
| `joule-repo-sync` | 회사 Gitea 의 Joule(`asec_autotest_tool`) 커밋을 개인 GitHub 사본에 덧붙여 동기화 — 차종 표준 DB 를 떨어내고 force push 없이 작성자·날짜 보존 (회사 → 개인 단방향, 푸시는 확인 후) |
| `redmine-daily-dashboard` | 매일 할당 일감을 수집해 어제 대비 변화·마감 임박·정체 건과 함께 Confluence 대시보드로 발행 |
| `redmine-issue` | 사내 Redmine 이슈·프로젝트를 REST API로 조회해 정리. 새 일감 생성과 내가 등록한 일감의 수정·코멘트까지 (미리보기 승인 후 전송) |
| `redmine-patch-issue` | eCoDY 패치 정리 페이지 하나를 읽어 SWP Delivery_Patch 적용용 Redmine **작업 지시서** 일감을 조립 — 작업 시간 순서의 목차, 단계마다 함정·완료 조건, 추측 대신 확인 방법 (미리보기 승인 후 전송, 사내망 전용) |
| `skill-repo-sync` | 계정 스킬을 이 저장소에 반영하고 커밋·푸시를 안내 |
| `slack-morning-briefing` | 직전 브리핑 이후의 슬랙 메시지를 정리해 매일 아침 대상 DM으로 전송 |
| `slack-to-calendar` | 슬랙 공지·일정 메시지를 파싱해 구글 캘린더에 등록 |
| `svg-creation` | 통일된 톤앤매너의 SVG 다이어그램·아이콘 생성 규약 |
| `swp-delivery-patch` | HAE mobilgene Classic SWP Delivery_Patch 를 당사 FBL·APP 에 적용 — eCoDY-IMS 수집, 배포본 판별, HAE 이전/현재 형상과 당사 설정의 3-way 판정, 적용·정적 검수·빌드 검수, 버전업, 실기 순서, 기록 (외부 쓰기는 승인 후) |
| `tech-research-to-confluence` | 기술 자료를 조사·기획해 다중 페이지 Confluence 가이드로 발행 |
| `travel-english-weekly` | 초중급 학습자용 해외여행 영어 회화 주간 학습 브리핑 |

`watchdog/` 는 스킬이 아니다 — 예약 실행이 실제로 돌았는지 점검하는 PowerShell 도구이고, 그래서 위 표에 없다.

계정에는 있지만 이 저장소에 두지 않은 스킬도 있다 (`python-dev`, `mcu-c-dev`, `office-file-slimmer`, `portfolio-theme`, `sw-tech-doc`, `wanted-resume-tailoring`, `ibu-diagspec`, `aspice-audit-process-check`, `aspice-audit-wp-check`, `aspice-audit-final-report`). 필요해지면 그때 추가한다.
