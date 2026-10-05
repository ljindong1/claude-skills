@echo off
rem ==========================================================================
rem  BuildVariants.bat  -  JENKINS_BUILD_TARGET = ALL : every combination
rem --------------------------------------------------------------------------
rem  Location : <project folder>\Build\   (same folder as Build.bat)
rem  Called by: Build_Hook_<MODEL>.bat when PJ_Define.h has
rem               #define JENKINS_BUILD_TARGET ALL
rem  Usage    : BuildVariants.bat <Build.bat action> [-jN]
rem  Steps    : base = OEUK option other than OEUK_TEST (e.g. OEUK_HE1I 26810)
rem             version +1 possible (all digits inside the OEUK block, APP)
rem               1) OEUK_HE1I 26810 -> Debug\OEUK_HE1I\26810\
rem               2) OEUK_TEST 26810 -> Debug\OEUK_HE1I\26810_test\
rem               3) OEUK_HE1I 26820 -> Debug\OEUK_HE1I\26820\     (version +1 :
rem               4) OEUK_TEST 26820 -> Debug\OEUK_HE1I\26820_test\  2nd digit, carry)
rem             otherwise (FBL HE130I02 : digits outside the block / letters)
rem               1) OEUK_HE1I -> Debug\OEUK_HE1I\HE130I02\       (version kept)
rem               2) OEUK_TEST -> Debug\OEUK_HE1I_TEST\
rem             only one OEUK option is enabled per build (others commented).
rem             PJ_Define.h is restored at the end - the temporary edits and
rem             the +1 version are NOT committed.
rem             a failed variant is reported, the others are still built.
rem  Exit     : 0 all ok / 31 some failed / 32 all failed / 33 plan error
rem             ALL_OK = number of built variants (returned to the hook)
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion

set "HOOK_DIR=%~dp0"
for %%I in ("%HOOK_DIR%..") do set "PROJ_DIR=%%~fI"
set "PJ_FILE=%PROJ_DIR%\Application\app_code\a_app_service\src\PJ_Define.h"
set "TOOL=%HOOK_DIR%PJ_Variant.ps1"
set "FIRST_ACT=%~1"
set "JOPT=%~2"
if "%FIRST_ACT%"=="" set "FIRST_ACT=Build"
rem  Rebuild only once - the next variants only change PJ_Define.h
set "NEXT_ACT=%FIRST_ACT%"
if /i "%FIRST_ACT%"=="Rebuild" set "NEXT_ACT=Build"

set "PLAN=%TEMP%\bv_plan_%RANDOM%%RANDOM%.txt"
set "BACKUP=%TEMP%\bv_pjdef_%RANDOM%%RANDOM%.h"
set "N=0"
set "OK=0"
set "FAIL=0"
set "RC=0"

rem ---- 1) build list --------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%TOOL%" -Action plan -File "%PJ_FILE%" > "%PLAN%"
if errorlevel 1 (
    type "%PLAN%"
    echo [VARIANTS] build list error - nothing built.
    set "RC=33"
    goto :end
)
echo [VARIANTS] build list :
type "%PLAN%"

rem ---- 2) build each variant ------------------------------------------------
copy /y "%PJ_FILE%" "%BACKUP%" > nul
for /f "usebackq tokens=1,2" %%A in ("%PLAN%") do call :one %%A %%B
copy /y "%BACKUP%" "%PJ_FILE%" > nul
echo [VARIANTS] PJ_Define.h restored.

rem ---- 3) result ------------------------------------------------------------
echo [VARIANTS] built !OK! / failed !FAIL!
if !FAIL! gtr 0 set "RC=31"
if !OK! equ 0 set "RC=32"

:end
if exist "%PLAN%" del /q "%PLAN%"
if exist "%BACKUP%" del /q "%BACKUP%"
endlocal & set "ALL_OK=%OK%" & exit /b %RC%

rem ---- one variant : %1 = OEUK option, %2 = version (KEEP = unchanged) -------
:one
set /a N+=1
set "ACT=%NEXT_ACT%"
if !N! equ 1 set "ACT=%FIRST_ACT%"
echo.
echo ===============================================================================
echo [VARIANTS] (!N!) %1 v%2 : Build.bat !ACT! %JOPT%
echo ===============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%TOOL%" -Action apply -File "%PJ_FILE%" -Variant %1 -Version %2
if errorlevel 1 (
    echo [VARIANTS] [FAIL] %1 v%2 - PJ_Define.h switch failed
    set /a FAIL+=1
    goto :eof
)
for %%E in (sre elf hex map) do if exist "%PROJ_DIR%\Debug\*.%%E" del /q "%PROJ_DIR%\Debug\*.%%E"
set "MARKER=%TEMP%\bv_marker_%RANDOM%%RANDOM%.tmp"
type nul > "%MARKER%"
pushd "%PROJ_DIR%"
call Build\Build.bat !ACT! %JOPT%
set "BRC=!ERRORLEVEL!"
popd
rem  Build.bat exit code alone is not reliable - require a new .elf
powershell -NoProfile -Command "$m=(Get-Item -LiteralPath '%MARKER%').LastWriteTime; $e=Get-ChildItem -LiteralPath '%PROJ_DIR%\Debug' -Filter *.elf -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $m }; if ($e) { exit 0 } else { exit 1 }"
if errorlevel 1 if "!BRC!"=="0" set "BRC=9"
del /q "%MARKER%"
if not "!BRC!"=="0" (
    echo [VARIANTS] [FAIL] %1 v%2 - build error !BRC!
    set /a FAIL+=1
    goto :eof
)
call "%HOOK_DIR%PostPackage.bat" %1
echo [VARIANTS] [OK] %1 v%2
set /a OK+=1
goto :eof
