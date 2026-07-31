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
├── aspice-audit-report/
│   ├── SKILL.md
│   ├── assets/                         # 체크리스트 템플릿(.xlsx)
│   ├── references/
│   └── scripts/                        # 매핑·판정·검증
├── confluence-project-page/
│   ├── SKILL.md
│   ├── assets/                         # 페이지 본문 HTML 템플릿
│   └── references/
├── confluence-writing/
│   ├── SKILL.md
│   └── references/
├── daily-standup/
│   └── SKILL.md
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
├── tech-research-to-confluence/
│   ├── SKILL.md
│   └── references/
└── travel-english-weekly/
    ├── SKILL.md
    └── references/                     # 표현 라이브러리
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
| `aspice-audit-report` | ASPICE 품질점검 체크리스트를 자동 1차 작성하고 사람 작성본과 대비해 일치율 측정·개선 |
| `confluence-project-page` | mobaseasec Confluence 에 신규 프로젝트 페이지 세트를 표준 템플릿으로 생성 |
| `confluence-writing` | Confluence 글쓰기 톤·구조·서식과 MCP 발행 규약의 정본 |
| `daily-standup` | 슬랙 데일리 스탠드업을 대화로 작성해 본인 이름으로 게시 |
| `skill-repo-sync` | 계정 스킬을 이 저장소에 반영하고 커밋·푸시를 안내 |
| `slack-morning-briefing` | 직전 브리핑 이후의 슬랙 메시지를 정리해 매일 아침 대상 DM으로 전송 |
| `slack-to-calendar` | 슬랙 공지·일정 메시지를 파싱해 구글 캘린더에 등록 |
| `svg-creation` | 통일된 톤앤매너의 SVG 다이어그램·아이콘 생성 규약 |
| `tech-research-to-confluence` | 기술 자료를 조사·기획해 다중 페이지 Confluence 가이드로 발행 |
| `travel-english-weekly` | 초중급 학습자용 해외여행 영어 회화 주간 학습 브리핑 |

계정에는 있지만 이 저장소에 두지 않은 스킬도 있다 (`python-dev`, `mcu-c-dev`, `office-file-slimmer`, `portfolio-theme`, `sw-tech-doc`, `wanted-resume-tailoring`, `confluence-cross-site-copy`). 필요해지면 그때 추가한다.
