# 모드 B — 폴더 추론 매핑 규칙 (설계서 v0.4 §4.3)

Target 시트 없이 폴더만으로 현황을 추론하고 Target 시트 초안을 역생성한다.
**모드 B 결과는 2단계 입력이 될 수 없다** (계약 규칙 1).

## 절차

1. B0 입력 검증: 폴더 존재·파일 수 (DELIVERABLE_ROOT_* 코드 공용).
   **폴더 안에서 Target* 시트를 가진 .xlsx가 발견되면
   `CHECKLIST_FOUND_IN_FOLDER`(PAUSE)** — "이 파일로 모드 A 진행"을 역제안하고
   사용자 선택을 기다린다 (자동 전환 금지). listing 모드에서는 파일을 열 수
   없어 이름 힌트("체크리스트"/"checklist")로만 추정해 안내한다.
2. B1 스캔: 문서/비문서 분리(config.DOCUMENT_EXTENSIONS 기준. 비문서는
   non_document_files로 집계만) + 문서 파일 무결성 검사(비정상은 추론 제외·별도 표기)
3. B2 결정론 추론: 파일명+상위 폴더 경로 NFC 정규화 → oii_map.json keyword_dict
   대조 → INFERRED_HIGH(단일 명확) / INFERRED_LOW(복수·부분) / UNCLASSIFIED(미매칭)
4. B3 골격 생성 (mode=folder_inferred, id=F-nnn)
5. **B4 AI 열람 게이트**: INFERRED_LOW·UNCLASSIFIED 건수를 사용자에게 보고하고
   열람 승인을 받는다. 과다하면 범위 축소를 안내 — 무단 대량 열람 금지.
6. B5 AI 내용 확인: 승인분만, 제목·목차·서두 수준. 분류 목적 한정.
   근거 인용 필수. 내용을 봐도 불명확하면 UNCLASSIFIED 유지 (추측 분류 금지).
   inference.decided_by="미확정".
7. B6 검증(전 문서 파일 inference 존재) → B7 대시보드(추론 배너 고정)
8. B8 사용자 게이트: 분류 검토·정정(human_decision) → 확정
9. B9 Target 시트 초안 역생성 (generate_target_draft.py):
   - assets/target_sheet_template.xlsx 양식, 추론 근거를 비고 열에 기재
   - 동일 그룹+동일 표준 산출물의 복수 파일은 한 행에 개행 다중 기재
   - **AI 초안 마커**: 숨김 시트 `_ai_draft_meta`(generated_by, generated_at,
     mapping revision, reviewed=false)

## 세탁 경로 차단

모드 A ⓪이 `_ai_draft_meta`를 검출하면 `AI_DRAFT_CHECKLIST`(PAUSE)로 정지하고
사람 검수 완료를 확인한다. 검수 확인 시 마커 reviewed=true 갱신 +
mapping.json source.draft_origin에 이력 기록. 마커는 보조 장치이며
"초안은 검수 후 편입"이라는 절차 규칙이 본선이다.
