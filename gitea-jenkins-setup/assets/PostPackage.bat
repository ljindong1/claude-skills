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
rem  Layout   : folder / version come from PJ_Variant.ps1 (-Action folder)
rem             APP (next version possible) : one folder per software version
rem               OEUK_TEST build -> <base OEUK>\<base ver>_test\ (same level)
rem               e.g. Debug\OEUK_HE1I\26810\  Debug\OEUK_HE1I\26810_test\
rem               same version  -> only that version folder is rebuilt
rem               other versions -> kept as they are
rem               loose files / rom_* folders directly under OEUK_xxxx (old flat
rem               layout of Build_all.bat) are removed.
rem             FBL (next version not possible) : flat, one folder per OEUK
rem               e.g. Debug\OEUK_HE1I\  Debug\OEUK_HE1I_TEST\
rem               same names as APP repo References\02_Fbl_Binary\ folders.
rem               the whole folder is rebuilt (old version folders removed).
rem             file prefix is the base model in both (he1i_psu_..._TEST too).
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

rem ---- 3) output folder / software version ---------------------------------
rem  PJ_Variant.ps1 -Action folder : "<folder> <version folder> <version>"
rem    APP OEUK_HE1I -> OEUK_HE1I 26810 26810
rem        OEUK_TEST -> OEUK_HE1I 26810_test 26810   (named by the BASE version)
rem    FBL OEUK_HE1I -> OEUK_HE1I . HE130I02         ("." = flat, no version folder)
rem        OEUK_TEST -> OEUK_HE1I_TEST . DEV30I02
rem  version digits: OEUK block first, then the common area (FBL HE130I02).
set "FOLDER_VARIANT="
set "VER_DIR="
set "VER_REAL="
if exist "%SCRIPT_DIR%PJ_Variant.ps1" (
    for /f "usebackq tokens=1,2,3" %%a in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%PJ_Variant.ps1" -Action folder -File "%VEHICLE_OPTION_FILE%" -Variant !VARIANT!`) do (
        if not defined FOLDER_VARIANT (
            set "FOLDER_VARIANT=%%a"
            set "VER_DIR=%%b"
            set "VER_REAL=%%c"
        )
    )
) else (
    echo [PostPackage] [WARNING] PJ_Variant.ps1 not found - version UNKNOWN.
)
if not defined VER_DIR set "VER_DIR=UNKNOWN"
if not defined FOLDER_VARIANT set "FOLDER_VARIANT=!VARIANT!"
if "!FOLDER_VARIANT!"=="[PJ_Variant]" (
    echo [PostPackage] [WARNING] PJ_Variant.ps1 error - version UNKNOWN.
    set "FOLDER_VARIANT=!VARIANT!"
    set "VER_DIR=UNKNOWN"
)
set "FLAT=0"
if "!VER_DIR!"=="." set "FLAT=1"
if "!FLAT!"=="1" (
    set "version=!VER_REAL!"
    if not defined version set "version=UNKNOWN"
) else (
    set "version=!VER_DIR:_test=!"
)
echo [PostPackage] Software version : !version!

rem ---- 4) compose model based name / version folder ------------------------
set "PREFIX_UPPER=!FOLDER_VARIANT:OEUK_=!"
set "PREFIX_UPPER=!PREFIX_UPPER:_TEST=!"
for /f "usebackq" %%p in (`powershell -Command "'!PREFIX_UPPER!'.ToLower()"`) do set "PREFIX_LOWER=%%p"
for /f "tokens=1,* delims=_" %%a in ("!ORIGINAL_BASE_NAME!") do set "SUFFIX=_%%b"
set "NEW_BASE_NAME=!PREFIX_LOWER!!SUFFIX!"
set "VARIANT_DIR=..\Debug\!FOLDER_VARIANT!"
if "!FLAT!"=="1" (
    rem FBL flat layout: one build per OEUK folder -> rebuild the whole folder
    set "OUTPUT_DIR=!VARIANT_DIR!"
    set "ROM_DIR=rom_!version!"
    if exist "!VARIANT_DIR!" rmdir /s /q "!VARIANT_DIR!"
) else (
    set "OUTPUT_DIR=!VARIANT_DIR!\!VER_DIR!"
    set "ROM_DIR=rom_!VER_DIR!"
    rem old flat layout: files and rom_* folders directly under VARIANT_DIR
    if exist "!VARIANT_DIR!\" (
        del /q "!VARIANT_DIR!\*.*" > nul 2> nul
        for /d %%D in ("!VARIANT_DIR!\rom_*") do rmdir /s /q "%%D"
    )
    rem same version -> rebuild only this version folder
    if exist "!VARIANT_DIR!\!VER_DIR!" rmdir /s /q "!VARIANT_DIR!\!VER_DIR!"
)
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
rem  only when a .s19 was built (FBL Build.bat makes no .s19 -> skipped)
set "HAS_S19=0"
if exist "!OUTPUT_DIR!\!NEW_BASE_NAME!.s19" set "HAS_S19=1"
if "!HAS_S19!"=="0" echo [PostPackage] No .s19 - rom package skipped.
if "!HAS_S19!"=="1" if not "!version!"=="UNKNOWN" (
    echo [PostPackage] Packaging for version !version! ...
    pushd "!OUTPUT_DIR!" > nul
    if not exist "!ROM_DIR!" mkdir "!ROM_DIR!"
    if exist "!NEW_BASE_NAME!.s19" copy "!NEW_BASE_NAME!.s19" "!ROM_DIR!\" > nul
    if exist "%SECUREFLASH_INI%" (
        copy "%SECUREFLASH_INI%" "!ROM_DIR!\" > nul
    ) else (
        echo [PostPackage] [WARNING] SecureFlash ini not found.
    )
    echo [PostPackage] Create zip file : !ROM_DIR!.zip
    tar -a -cf "!ROM_DIR!.zip" "!ROM_DIR!"
    popd > nul
)

echo [PostPackage] Finished for !VARIANT! v!version!.

:done
endlocal
exit /b 0
