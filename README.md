# claude-skills

Claude Code 커스텀 스킬 모음. Claude 클라우드 루틴(JIns 환경)이 세션 시작 시 이 저장소를 clone 해 `~/.claude/skills/` 로 설치하고, 루틴 실행 중 필요한 스킬을 로드해 사용한다.

## 저장소 구조

```
claude-skills/
├── README.md
├── setup-script.sh                     # 클라우드 환경 부팅 시 스킬 설치용 스크립트
└── .claude/skills/
    ├── slack-morning-briefing/
    │   └── SKILL.md
    ├── slack-to-calendar/
    │   └── SKILL.md
    ├── arxml-analyzer/
    │   ├── SKILL.md
    │   ├── references/                 # 개념 설명·용어집·예시
    │   └── scripts/                    # ARXML 검사·변환 스크립트
    ├── aspice-audit-report/
    │   ├── SKILL.md
    │   ├── assets/                     # 빈 체크리스트 템플릿(.xlsx)
    │   ├── references/
    │   └── scripts/                    # 매핑·판정·검증 스크립트
    ├── confluence-project-page/
    │   ├── SKILL.md
    │   ├── assets/                     # 페이지 본문 HTML 템플릿
    │   └── references/
    ├── confluence-writing/
    │   └── SKILL.md
    ├── daily-standup/
    │   └── SKILL.md
    ├── svg-creation/
    │   └── SKILL.md
    └── travel-english-weekly/
        ├── SKILL.md
        └── references/                 # 표현 라이브러리
```

- 스킬의 이름은 파일명이 아니라 **폴더명**으로 정해진다. 각 스킬은 자기 폴더 안에 `SKILL.md` 를 둔다(보조 스크립트·자료가 있으면 같은 폴더에 함께 둔다).
- 스킬을 추가하려면 `.claude/skills/<스킬이름>/SKILL.md` 를 새로 만들면 된다. 설치 스크립트는 `.claude/skills/` 아래를 통째로 복사하므로 **폴더만 추가하면 자동 반영**되고 스크립트는 고칠 필요가 없다.

## 클라우드 루틴에 등록하는 법

클라우드 환경은 세션마다 빈 컨테이너로 초기화되므로 스킬을 안에 영구 저장할 수 없다. 대신 **세션 시작 시 실행되는 설정 스크립트**에서 이 저장소를 받아 스킬을 설치한다.

1. `setup-script.sh` 의 `REPO_URL` 을 이 저장소 주소로 바꾼다.
2. 그 내용을 클라우드 환경(JIns) 설정의 **"설정 스크립트"** 칸에 붙여넣고 저장한다.
3. 루틴을 실행하면 세션 로그에 `[설치 완료] 스킬 N개:` 와 설치된 스킬 목록이 출력된다.

설치 스크립트는 clone 실패·스킬 폴더 부재·설치 0개를 각각 검증(assert)해 조용히 실패하지 않고 에러로 멈춘다.

## 스킬 목록

| 스킬 | 용도 |
| --- | --- |
| `slack-morning-briefing` | 직전 브리핑 이후의 슬랙 메시지를 정리해 매일 아침 대상 DM으로 전송 |
| `slack-to-calendar` | 슬랙 공지·일정 메시지를 파싱해 구글 캘린더에 등록 |
| `arxml-analyzer` | AUTOSAR ARXML 구조를 개념 중심으로 정리해 Confluence 에 보고 |
| `aspice-audit-report` | ASPICE 품질점검 체크리스트를 자동 1차 작성하고 사람 작성본과 대비해 일치율 측정·개선 |
| `confluence-project-page` | mobaseasec Confluence 에 신규 프로젝트 페이지 세트를 표준 템플릿으로 생성 |
| `confluence-writing` | 사내 Confluence(TECH 스페이스) 글쓰기 톤·구조·서식 규약 |
| `daily-standup` | 슬랙 #daily-standup 데일리 스탠드업을 대화로 작성해 본인 이름으로 게시 |
| `svg-creation` | Claude 브랜드 톤에 맞춘 SVG 다이어그램·아이콘 생성 규약 |
| `travel-english-weekly` | 초중급 학습자용 해외여행 영어 회화 주간 학습 브리핑 |

## 스킬 수정

스킬 내용을 바꿀 땐 해당 `SKILL.md` 만 수정해 커밋하면 된다. 설치 스크립트가 매 세션마다 최신을 새로 받아오므로 클라우드 환경 설정은 다시 건드릴 필요가 없다.

