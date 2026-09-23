{PROJECT}  -  CVD 보드 라이팅 설정
=====================================================================
생성    : {DATE}   (cvd-project-setup 스킬)
차종    : {MODEL} / {CTRL}
MCU     : {MCU}
도너    : {DONOR}
폴더    : {FOLDER}
저장소  : {REPO}


[사용]
---------------------------------------------------------------------
1) CVD 실행, 보드 연결
2) 툴바의 빨간 PS (Project Select) -> {UPPER}
   툴바가 안 보이면 명령창에 직접 입력
      CD.DO C:\JnDTech\CVI\CVD\S32_Config\loadfile.cmm
3) 툴바 버튼 4개가 생긴다 (버튼에는 2글자만 찍힌다)
      PD  Program DownLoad   라이팅
      PA  Path Set           심볼 / 소스 로드 (디버깅)
      RE  Reset
      WI  Window             워치 창
4) PD -> Image&Hsm -> file load start
5) "Erase flash memory?" 가 뜬다
      Yes : 워크 플래시(NvM/Fee) + 코드 플래시를 지운다. SFlash 는 안 건드린다.
            보드 이력을 모르면 이것.
      No  : NvM 을 남긴다. DTC / 학습값 보존.
6) 보드 전원 재인가


[써 넣는 이미지]
---------------------------------------------------------------------
loadimage.txt 에 적혀 있다. 모두 {REPO} 기준.

  FBL   {FBL}
  APP   {APPW}
  HSM   {HSM}

심볼(PA)용은 따로다.
  ELF   {APPE}

주의 : 같은 폴더의 접미사 없는 .s19 는 리프로그래밍(OTA)용이다.
       라이팅에는 반드시 _Writing.s19 를 쓴다.

빌드가 새로 나오면 파일명이 바뀐다. 그때는 스킬로 목록만 갱신한다.
      python scripts\cvdsetup.py images --repo "{REPO}"


[하지 말 것]
---------------------------------------------------------------------
cyt2blx_flash_erase_all.CSF 는 실행하지 않는다.

SFlash 13개 섹터를 지우는데 HSM 이미지가 되돌려 놓는 것은 5개뿐이다.
나머지 8개(4,5,6,7,53,54,55,59)는 지워진 채로 남고 저장소 어느 이미지에도
그 내용이 없다. 칩 출하 시 기록되는 값으로 보이므로 보드를 못 쓰게 될 수 있다.

Program DownLoad 의 "Erase flash memory? Yes" 는 안전하다. 코드/워크 플래시만
지우고 SFlash 는 건드리지 않는다.


[상태 표시]
---------------------------------------------------------------------
SYSOFF    디버거가 타겟에 안 붙은 상태. 시작 전 정상.
SYSDOWN   라이팅 스크립트가 끝나면서 sys.down 한 상태. 실패가 아니다.
          "Reset Target" 이 찍혔으면 기록까지 끝난 것이다.
DEBUG     PA 후 CPU 가 정지한 채 붙어 있는 상태. 디버깅 시작점.

PA 를 먼저 하고 RE 를 눌러야 한다. RE(Reset.cmm)는 go main 을 하므로
심볼이 없으면 브레이크포인트를 0x00000000 에 걸려다 실패한다.


[이 폴더는 자립해 있다]
---------------------------------------------------------------------
플래시 로더 TVII-B-E-2M.out / TVII-B-H-8M.out 을 폴더 안에 품고 있고,
.csf 의 &FLASH_LOADER 경로가 전부 이 폴더를 가리킨다.
다른 프로젝트 폴더를 지우거나 옮겨도 영향받지 않는다.


[원본 대비 변경]
---------------------------------------------------------------------
{DONOR} 를 복제한 뒤
  - 폴더명을 {PROJECT} 로 치환
  - Path.cmm 의 심볼 ELF 경로와 소스 트리 경로를 이 저장소로 지정
  - loadimage.txt 를 이 저장소 바이너리로 작성
  - &FLASH_LOADER 경로를 전부 이 폴더 기준으로 재지정
  - loadfile.cmm 에 {UPPER} 블록 추가 (백업 후 추가만, 기존 블록 무수정)

검증은 아래로 다시 볼 수 있다.
      python scripts\cvdsetup.py verify --name {PROJECT} --donor {DONOR}
