# 문제 대응

HE1I PSU 첫 적용(2026-09-16~17)에서 실제로 겪은 사례 중심. 모든 조치는 **수정·삭제 없이** 한다. 기존 자원을 고쳐야 하면 사용자에게 방법을 안내하고 사용자가 직접 한다.

## 사전 점검

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| `preflight`에서 gitea `http: 401` | 토큰 오타·만료·권한 부족 | `token_guide.md` 2절로 재발급 (repository 읽기·쓰기) |
| jenkins `http: -1`, SSL 문구 | 사내 인증서 | `setx JENKINS_INSECURE 1` 후 터미널 재시작 |
| 환경변수를 등록했는데 `false` | `setx`는 새 프로세스부터 적용 | VS Code·Claude Code 완전 종료 후 재실행 |
| 사내 주소 연결 불가 | 웹·Cowork 샌드박스에서 실행 | Claude Code CLI(사용자 PC)에서만 실행 |

## Gitea

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| `fork` conflict: 같은 이름 저장소가 Fork가 아님 | 본인 계정에 동명 저장소 존재 | 사용자에게 알리고 중단. 기존 저장소 처리는 사용자가 결정 |
| `collab` conflict: 권한 read | 이전에 읽기로 추가됨 | 사용자가 저장소 설정 → 공동작업자에서 쓰기로 변경 |
| 원본 저장소 404 | 권한 없는 비공개 저장소는 404로 보임 | 원본 담당자에게 읽기 권한 요청 (예: `git/psu_master`는 일반 계정에 404) |

## 로컬 git

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| 서브모듈 `Repository not found` | 서브모듈 저장소 권한 없음 | 경고만. 빌드가 서브모듈을 쓰는지 `Build.bat`·`Build_Hook*.bat`에서 서브모듈 폴더명을 검색해 판단. PSU는 `Build_all.bat`만 참조(없으면 건너뜀)라 불필요했음 |
| `warning: use of unencrypted HTTP remote URLs` | 사내 Gitea가 HTTP | 무시 |
| bat 파일 줄바꿈이 LF로 바뀜 | `sed` 등 편집 도구 | skill은 assets를 바이너리 그대로 복사하므로 발생하지 않음. 사용자가 수동 편집 후엔 CRLF 확인. 저장소가 `core.autocrlf=true`면 Gitea에는 LF로 보이는 것이 정상 |
| `add-bat` conflict | 같은 이름 bat이 이미 있고 내용 다름 | 덮어쓰지 않음. 기존 파일 사용 여부를 사용자와 결정 |
| push 시 인증 창 | Chrome 모드(토큰 없음)에서 git 자격 증명 미저장 | 사용자가 한 번 로그인해 Windows 자격 증명 관리자에 저장 |

## Jenkins

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| 템플릿 Job `EXAMPLE_CAR_AUTOSAR_ASEC`이 404 | 일반 계정에 권한 없음 | 이 skill은 템플릿 XML로 새로 만드므로 영향 없음. 인증정보 ID만 운영 Job(`ASEC_BJ1_PSU`)에서 읽음 |
| `job-create` HTTP 403 | Job 생성 권한 없음 또는 crumb 문제 | 뷰 경로 없이 재시도 판단, 반복되면 Jenkins 관리자에게 Job 생성 권한 요청 |
| `job-create` HTTP 400/500 | 플러그인 XML 형식 차이 | 응답 문구를 사용자에게 보여주고 중단. 참고 Job의 `config.xml` 구조와 비교 |
| **연속 빌드** (결과물 커밋에 반응) | 제외 필터 앞뒤 공백, `(?s)` 누락 | 실제 사례: 붙여 넣기로 앞 공백 3칸 + `(?s)` 누락 → #1 뒤 #2·#3 연속. skill은 값을 직접 넣고 `job-verify`의 `exclusion_exact`로 확인하므로 재발하지 않음. 이미 발생하면 사용자가 추가 빌드를 ✕로 중단하고 필터를 `(?s).*Auto commit from Jenkins.*`로 수정 |
| `Build ERROR LEVEL` 9 | 새 `.elf`가 없음 (컴파일 실패) | 로그의 컴파일 오류 확인. `Build.bat` 종료 코드만으로는 실패가 가려질 수 있어 표준 Hook이 `.elf`로 재판정 |
| `Git Push ERROR LEVEL` ≠ 0 | build 계정 권한, 빌드 중 같은 브랜치 push | 공동작업자 쓰기 확인, 다음 push로 재빌드 |
| 첫 `git fetch`에서 `Failed to authenticate user` 후 재시도 성공 | 일시적 인증 지연 | 무시. 반복되면 Jenkins 인증정보 확인 |

## 관련 문서 (사내 Confluence TECH 스페이스)

- [Mobase] Jenkins 빌드 가이드 → 3번 빌드 흐름, 5번 Job 설정 3.1절(필터), 7번 트러블슈팅 B(무한 빌드)
- [부록1] 실전 적용 절차 (HE1I PSU 사례), [부록2] 표준 배치 파일과 Job 설정
