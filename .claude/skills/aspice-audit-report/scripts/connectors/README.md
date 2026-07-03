# 시스템 커넥터 (사내망 실행 전용)

사내망에서 REST API로 시스템 근거를 끌어와, "확인 필요"로 남던 항목을 데이터 기반 판정으로 전환한다.
**샌드박스에서는 사내망에 닿지 않으므로 반드시 사내망 PC에서 실행한다.**

## 설정
1. `pip install requests`
2. `connectors_config.example.json` → `connectors_config.json` 복사 후 URL·API 키 입력.
   (또는 환경변수 `REDMINE_URL`, `REDMINE_API_KEY` 사용 — 환경변수가 우선)
3. 토큰은 비밀: `connectors_config.json`을 커밋하지 말 것.

## 레드마인 (redmine_client.py)
```
python redmine_client.py --summary --project swrc_cn8        # 이슈 tracker/status 분포
python redmine_client.py --issue 43641                       # 부적합 ID 존재·상태 검증
python redmine_client.py --summary --project swrc_cn8 --out redmine_evidence.json
```

### 점검에 어떻게 쓰는가
- **부적합 ID 연계**: Fail 항목의 레드마인 이슈 번호를 `--issue`로 검증(존재·상태). 없는 ID면 정합성 오류.
- **문제해결 관리 절차 항목**: `--summary`의 tracker/status 분포로 이슈 등록·조치·종료가 실제로 관리되는지 근거 확보.
  - 단, "절차를 제대로 따랐는가"의 최종 Pass 판정은 규칙/사람 몫. API는 데이터(객관 근거)를 제공할 뿐이다.

### 주의 (반드시)
- 엔드포인트·커스텀필드 ID는 레드마인 버전/설정마다 다르다. 인스턴스에서 한 번 검증하고 필요시 코드를 맞춰라.
- 사내 자체서명 인증서면 `verify_ssl: false` 로 둔다(경고가 뜨며, 사내망 한정 사용).
- API는 "이슈가 있다/상태가 이렇다"는 사실을 줄 뿐, 일관성·적정성 판단은 별도 규칙이 필요하다.

## 다음 후보 (동일 패턴으로 확장)
- codebeamer: REST v3 (`/api/v3/items`, relations) — 추적성·요구사항·베이스라인.
- git(Gitea): REST API — 레포 존재·최신 커밋.
- PMS(커스텀): 공개 API 확인 필요. 없으면 Claude in Chrome 화면 읽기로 대체.
