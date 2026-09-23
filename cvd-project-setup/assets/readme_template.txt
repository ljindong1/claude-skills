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


[Project Select 에 어떻게 올라가 있나]
---------------------------------------------------------------------
이름이 두 가지다. 헷갈리기 쉬우니 구분해 둔다.

  {PROJECT}    폴더 이름.        실제 스크립트가 들어 있는 곳
  {UPPER}    CHOOSEBOX 라벨.  Project Select 창에 뜨는 이름

라벨 쪽은 S32_Config 바로 아래의 공용 파일 loadfile.cmm 에 블록으로 등록돼
있다. 실행 코드는 없고 "이 항목을 고르면 CPU 를 이걸로 잡고 툴바를 이렇게
깔아라"는 등록표다.

  POS ...                        Project Select 창에서의 위치 (열, 행)
  CHOOSEBOX "..."                화면에 뜨는 이름 = {UPPER}
  DIALOG.END                     고르면 선택창을 닫는다
  B::sys.CPU <CPU>               CPU 설정                       <- 핵심
  MENU.ReProgram ADD TOOLBAR     아래 버튼들을 툴바에 붙인다
     TOOLITEM "Program DownLoad" "PD,R"  CD.DO ...\{PROJECT}\loadimage.cmm
     TOOLITEM "Program Edit"     "Ed,B"  Pedit ...\{PROJECT}\loadimage.cmm
     TOOLITEM "Path Set"         "PA,R"  CD.DO ...\{PROJECT}\Path.cmm
     TOOLITEM "Path Edit"        "Ed,B"  Pedit ...\{PROJECT}\Path.cmm
     TOOLITEM "Reset"            "RE,R"  CD.DO ...\{PROJECT}\Reset.cmm
     TOOLITEM "Window"           "WI,G"  CD.DO ...\{PROJECT}\swp_debug_watch.cmm

버튼 하나가 스크립트 하나를 실행하는 연결일 뿐이다. 실제 일은 전부 이 폴더
안의 스크립트가 한다. 플래시 지우는 주소, 뱅크 전환, 로더 올리기는 .csf 에
있다.

TOOLITEM 의 두 번째 문자열이 버튼에 찍히는 2글자다. 첫 문자열은 마우스를
올렸을 때 뜨는 툴팁이라 버튼에는 안 보인다.

주의할 점 세 가지. 블록을 손으로 복제할 때 실제로 겪은 것들이다.

  - sys.CPU 를 다른 계열(CYT2B9 등) 블록에서 복제하면 CPU 가 엉뚱하게 박힌다.
    설정은 멀쩡해 보이는데 플래시가 다른 주소에 써진다.
  - Path Set / Path Edit 줄이 빠진 블록을 복제하면 PA 버튼 자체가 안 생겨
    Path.cmm 을 호출할 수 없다.
  - CHOOSEBOX 라벨의 대소문자가 어긋나면 중복 등록 검사를 통과해 같은
    프로젝트가 두 번 뜬다.

loadfile.cmm 은 12개 넘는 프로젝트가 ;#### 구분선으로 나열된 공용 파일이다.
스킬은 백업을 남기고 블록을 추가만 하며 기존 블록은 건드리지 않는다.


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


[무인 연결 확인]
---------------------------------------------------------------------
보드에 아무것도 쓰지 않고 연결 상태만 자동으로 확인할 수 있다.

    python scripts\cvdsetup.py run --mode check --repo "{REPO}"

CVD 가 스스로 떴다가 5초 안에 종료하고, 결과를 판정해 보여준다.
확인하는 것은 두 가지다.

  1. 타겟에 붙는가          Path.cmm 을 그대로 호출
  2. FBL 이 올라가 있는가   0x10028000 벡터 테이블 (초기 SP / 리셋 벡터)

산출물은 이 폴더의 _autorun\ 에 남는다 (check.cmm, check_log.txt).
지워도 되고, 다시 실행하면 새로 만들어진다.

라이팅(쓰기)은 아직 자동화되지 않았다. 벤더 스크립트의
DIALOG.YESNO "Erase flash memory?" 가 무인 실행을 막는다.


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
