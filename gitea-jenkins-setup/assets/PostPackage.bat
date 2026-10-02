@echo off
rem ==========================================================================
rem  PostPackage.bat  -  build artifact packaging
rem --------------------------------------------------------------------------
rem  Location : <project folder>\Build\   (same folder as Build.bat)
rem  Called by: Build_Hook_<MODEL>.bat  (after Build.bat, before GitPush.bat)
rem  Purpose  : reproduce the [Post-build] Archiving step of Build_all.bat so
rem             that Jenkins builds also produce
rem               - Debug\OEUK_xxxx\<ver>\<model>_psu_app_vX_Y_Z.*  artifacts
rem               - Debug\OEUK_xxxx\<ver>\rom_<ver>\               aSIMS sign input
rem  Layout   : one folder per software version (SOFTWARE_VERSION_0..4).
rem             OEUK_TEST build -> <base OEUK>\<ver>_test\ (same level as <ver>)
rem               e.g. Debug\OEUK_HE1I\26810\  Debug\OEUK_HE1I\26810_test\
rem             same version  -> only that version folder is rebuilt
rem             other versions -> kept as they are
rem             loose files / rom_* folders directly under OEUK_xxxx (old flat
rem             layout of Build_all.bat) are removed.
rem  Usage    : PostPackage.bat [OEUK_XXXX]
rem             no argument -> auto detect the enabled OEUK option
rem  Note     : logic based on Build_all.bat [Post-build] block.
rem             Build_all.bat itself is NOT modified (it still uses the flat
rem             layout and wipes the whole OEUK_xxxx folder).
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "VEHICLE_OPTION_FILE=..\Application\app_code\a_app_service\src\PJ_Define.h"
set "SECUREFLASH_INI=%SCRIPT_DIR%..\References\Doc_MB\02_Signed_Firmware_CFG\Autron_CYT2BLXX_SecureFlash2_psu_v300.ini"
set "BUILDWARNING_EXE=D:\BuildWarning\BuildWarning_Build.exe"

rem ---- 1) resolve target variant -------------------------------------------
set "VARIANT=%~1"
if not defined VARIANT (
    for /f "usebackq" %%i in (`powershell -Command "Select-String -Path '%VEHICLE_OPTION_FILE%' -Pattern '^\s*#define\s+(OEUK_\w+)' -AllMatches | ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value }"`) do (
        if not defined VARIANT set "VARIANT=%%i"
    )
)
if not defined VARIANT (
    echo [PostPackage] No enabled OEUK option found. Skipping.
    goto :done
)
echo [PostPackage] Target variant : !VARIANT!

rem ---- 2) find built artifact base name ------------------------------------
set "ORIGINAL_BASE_NAME="
for %%f in (..\Debug\*.sre) do set "ORIGINAL_BASE_NAME=%%~nf"
if not defined ORIGINAL_BASE_NAME (
    echo [PostPackage] No .sre file in Debug folder. Skipping.
    goto :done
)
echo [PostPackage] Built artifact  : !ORIGINAL_BASE_NAME!

rem ---- 3) software version of the variant ----------------------------------
set "version="
for /f "usebackq" %%V in (`powershell -Command "$c = Get-Content '%VEHICLE_OPTION_FILE%' | Out-String; if ($c -match '(?s)defined\s*\(\s*!VARIANT!\s*\)(.*?)#(elif|else|endif)') { $b = $matches[1]; $v = ''; 0..4 | ForEach-Object { if ($b -match ('#define\s+SOFTWARE_VERSION_' + $_ + '\s+\(u8\)''(.)''')) { $v += $matches[1] } }; Write-Output $v }"`) do (
    set "version=%%V"
)
if not defined version (
    echo [PostPackage] [WARNING] Could not extract software version. Defaulting to UNKNOWN.
    set "version=UNKNOWN"
)
echo [PostPackage] Software version : !version!

rem ---- 3-1) OEUK_TEST -> <base>\<ver>_test ----------------------------------
rem  test build goes next to the base build: Debug\OEUK_HE1I\26810_test\
rem  base = first OEUK option (enabled or commented) other than OEUK_TEST
set "FOLDER_VARIANT=!VARIANT!"
set "VER_DIR=!version!"
if /i "!VARIANT!"=="OEUK_TEST" (
    set "BASE_VARIANT="
    for /f "usebackq" %%i in (`powershell -Command "Select-String -Path '%VEHICLE_OPTION_FILE%' -Pattern '^\s*(//)?\s*#define\s+(OEUK_\w+)' -AllMatches | ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[2].Value } | Where-Object { $_ -ne 'OEUK_TEST' }"`) do (
        if not defined BASE_VARIANT set "BASE_VARIANT=%%i"
    )
    if defined BASE_VARIANT (
        set "FOLDER_VARIANT=!BASE_VARIANT!"
        set "VER_DIR=!version!_test"
    ) else (
        echo [PostPackage] [WARNING] No base OEUK option - using OEUK_TEST folder.
    )
)

rem ---- 4) compose model based name / version folder ------------------------
set "PREFIX_UPPER=!FOLDER_VARIANT:OEUK_=!"
for /f "usebackq" %%p in (`powershell -Command "'!PREFIX_UPPER!'.ToLower()"`) do set "PREFIX_LOWER=%%p"
for /f "tokens=1,* delims=_" %%a in ("!ORIGINAL_BASE_NAME!") do set "SUFFIX=_%%b"
set "NEW_BASE_NAME=!PREFIX_LOWER!!SUFFIX!"
set "VARIANT_DIR=..\Debug\!FOLDER_VARIANT!"
set "OUTPUT_DIR=!VARIANT_DIR!\!VER_DIR!"

rem old flat layout: files and rom_* folders directly under VARIANT_DIR
if exist "!VARIANT_DIR!\" (
    del /q "!VARIANT_DIR!\*.*" > nul 2> nul
    for /d %%D in ("!VARIANT_DIR!\rom_*") do rmdir /s /q "%%D"
)

rem same version -> rebuild only this version folder
if exist "!OUTPUT_DIR!" rmdir /s /q "!OUTPUT_DIR!"
mkdir "!OUTPUT_DIR!"
echo [PostPackage] Output folder    : !OUTPUT_DIR!

rem ---- 5) build warning report (optional) ----------------------------------
if exist "%BUILDWARNING_EXE%" (
    echo [PostPackage] Generating build warning report...
    cd ..
    call "%BUILDWARNING_EXE%"
    cd Build
    if exist "..\Debug\*BuildWarning.xlsx" move "..\Debug\*BuildWarning.xlsx" "!OUTPUT_DIR!\" > nul
) else (
    echo [PostPackage] BuildWarning exe not found - skipping warning report.
)

rem ---- 6) move artifacts ---------------------------------------------------
echo [PostPackage] Moving artifacts to !OUTPUT_DIR! ...
for %%E in (sre elf hex map) do (
    if exist "..\Debug\!ORIGINAL_BASE_NAME!.%%E" move "..\Debug\!ORIGINAL_BASE_NAME!.%%E" "!OUTPUT_DIR!\" > nul
)
if exist "..\Debug\*.s19" move "..\Debug\*.s19" "!OUTPUT_DIR!\" > nul 2> nul

rem ---- 7) rename to model based name ---------------------------------------
if not "!NEW_BASE_NAME!"=="!ORIGINAL_BASE_NAME!" (
    echo [PostPackage] Renaming artifacts to !NEW_BASE_NAME! ...
    pushd "!OUTPUT_DIR!" > nul
    ren "!ORIGINAL_BASE_NAME!.*" "!NEW_BASE_NAME!.*" > nul
    if exist "!ORIGINAL_BASE_NAME!_Writing.s19" ren "!ORIGINAL_BASE_NAME!_Writing.s19" "!NEW_BASE_NAME!_Writing.s19" > nul
    popd > nul
)

rem ---- 8) rom_<version> package (aSIMS sign input) -------------------------
if not "!version!"=="UNKNOWN" (
    echo [PostPackage] Packaging for version !version! ...
    pushd "!OUTPUT_DIR!" > nul
    if not exist "rom_!version!" mkdir "rom_!version!"
    if exist "!NEW_BASE_NAME!.s19" copy "!NEW_BASE_NAME!.s19" "rom_!version!\" > nul
    if exist "%SECUREFLASH_INI%" (
        copy "%SECUREFLASH_INI%" "rom_!version!\" > nul
    ) else (
        echo [PostPackage] [WARNING] SecureFlash ini not found.
    )
    echo [PostPackage] Create zip file : rom_!version!.zip
    tar -a -cf "rom_!version!.zip" "rom_!version!"
    popd > nul
)

echo [PostPackage] Finished for !VARIANT! v!version!.

:done
endlocal
exit /b 0
