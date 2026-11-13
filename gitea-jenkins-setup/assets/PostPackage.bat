@echo off
rem ==========================================================================
rem  PostPackage.bat  -  build artifact packaging  (project independent)
rem --------------------------------------------------------------------------
rem  Location : <project folder>\Build\   (same folder as Build.bat)
rem  Called by: Build_Hook_<MODEL>.bat  (after Build.bat, before GitPush.bat)
rem             BuildVariants.bat       (once per variant, arg1 = OEUK option)
rem  Purpose  : reproduce the [Post-build] Archiving step of Build_all.bat so
rem             that Jenkins builds also produce the artifact folder and the
rem             rom_<version> package (aSIMS sign input).
rem --------------------------------------------------------------------------
rem  TWO HALVES - this file has NO project specific branch.
rem
rem  1) COLLECT  (anchored on Debug, identical for every project)
rem       Debug\*.sre              -> base name of this build (newest wins)
rem       Debug\<base>.elf/.hex/.map
rem       Debug\*.s19              -> all of them
rem       Debug\*BuildWarning.xlsx
rem
rem  2) PLACE    (declared by the hook - two independent axes)
rem       Debug\ [ <variant>\ ] [ <version>\ ]
rem         variant axis : on when the build carries a signature verify key,
rem                        so a TEST variant exists        -> OEUK_<MODEL>\
rem         version axis : on when artifacts are kept per customer version
rem                        (up/downgrade evaluation, APP)  -> <version>\
rem       "." in a token means that axis is OFF.
rem
rem       psu_app   (dual bank APP)   variant+version  Debug\OEUK_HE1I\26810\
rem       psu_fbl   (dual bank FBL)   variant only     Debug\OEUK_HE1I\
rem       tpms FBL  (single bank FBL) variant only     Debug\OEUK_LT2\
rem       tpms APP  (single bank APP) version only     Debug\26B100\
rem --------------------------------------------------------------------------
rem  DECLARATION - the hook sets ONE of these (see Build_Hook_<MODEL>.bat):
rem    (a) PKG_RESOLVER_FILE   PJ_Define.h; PJ_Variant.ps1 decides both axes.
rem                            This is the default when nothing is declared.
rem    (b) PKG_VERSION_FILE    any file + PKG_VERSION_PATTERN (.NET regex with
rem        PKG_VERSION_PATTERN one capture group) -> version axis only.
rem    (c) PKG_FOLDER          literal "<variant> <verdir> <version>".
rem  Optional:
rem    PKG_ROM_S19             which .s19 goes into rom_ (default <base>.s19)
rem    SECUREFLASH_INI         ini for rom_ (default References\*Signed_Firmware*\*.ini)
rem
rem  Nothing resolves -> the version token of the artifact name is used
rem  (e_..._app_v2111 -> v2111) and a WARNING block is printed. Packaging is
rem  never skipped silently: a SUCCESS build always leaves a packaged folder.
rem --------------------------------------------------------------------------
rem  Usage    : PostPackage.bat [OEUK_XXXX]
rem             arg1 is only used in resolver mode (BuildVariants passes it)
rem  Note     : Build_all.bat is NOT modified (it still wipes OEUK_xxxx and
rem             uses the flat layout on local runs).
rem --------------------------------------------------------------------------
rem  CMD GOTCHA - every value handed to PowerShell goes through an environment
rem  variable ($env:PKG_*), never inlined into the command line. With delayed
rem  expansion on, a line that contains !VAR! is parsed a second time and the
rem  extra pass EATS one level of carets, so a regex anchor ^ silently turns
rem  into an unanchored match. That made the OEUK scan pick the commented out
rem  "// #define OEUK_TEST" line (verified 2026-11-13). Keeping !VAR! out of
rem  the PowerShell lines removes that whole class of bug. The OEUK scan also
rem  avoids ^ entirely by using TrimStart/StartsWith instead of an anchor.
rem  Pipes inside a usebackq backquote block must NOT be escaped ("^|" would
rem  reach PowerShell as a literal caret); in the 'single quoted' for /f form
rem  they must be ("2^>nul ^| findstr").
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass"
set "PKG_DEBUG_DIR=%SCRIPT_DIR%..\Debug"

rem  default declaration : resolver on the standard PJ_Define.h path.
rem  gjsetup.py --pj-define rewrites this literal for repositories that keep
rem  PJ_Define.h somewhere else.
if not defined PKG_RESOLVER_FILE if not defined PKG_VERSION_FILE if not defined PKG_FOLDER (
    set "PKG_RESOLVER_FILE=..\Application\app_code\a_app_service\src\PJ_Define.h"
)

rem  SecureFlash ini - do NOT hardcode a path here. The dedicated hook may
rem  pass SECUREFLASH_INI; otherwise it is looked up under References.
rem  The folder name (Doc_MB / Doc_MobaseElec), its number prefix (02_ / 03_)
rem  and the file name all differ per project. Projects that have no such ini
rem  (FBL) leave it unset and get the WARNING below - that is expected.
if not defined SECUREFLASH_INI (
    for /f "delims=" %%F in ('dir /b /s "%SCRIPT_DIR%..\References\*.ini" 2^>nul ^| findstr /i "Signed_Firmware"') do (
        if not defined SECUREFLASH_INI set "SECUREFLASH_INI=%%F"
    )
)
set "BUILDWARNING_EXE=D:\BuildWarning\BuildWarning_Build.exe"

rem ==========================================================================
rem  1) COLLECT - what this build produced, read from Debug only
rem ==========================================================================
rem  newest .sre wins. BuildVariants.bat clears Debug\*.sre before each build,
rem  but on the single build path a failed move could leave an older one and
rem  picking it would package the wrong artifact under the right name.
set "ORIGINAL_BASE_NAME="
for /f "usebackq delims=" %%f in (`%PS% -Command "$f=Get-ChildItem -LiteralPath $env:PKG_DEBUG_DIR -Filter *.sre -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($f) { $f.BaseName }"`) do set "ORIGINAL_BASE_NAME=%%f"
if not defined ORIGINAL_BASE_NAME (
    echo [PostPackage] No .sre file in Debug folder. Nothing to package.
    goto :done
)
set "PKG_BASENAME=%ORIGINAL_BASE_NAME%"
echo [PostPackage] Built artifact   : %ORIGINAL_BASE_NAME%

rem ==========================================================================
rem  2) PLACE - resolve the two axes
rem ==========================================================================
set "AX_VARIANT="
set "AX_VERDIR="
set "AX_VER="
set "AX_SRC="

if defined PKG_FOLDER call :resolve_literal
if not defined AX_SRC if defined PKG_VERSION_FILE call :resolve_version
if not defined AX_SRC if defined PKG_RESOLVER_FILE call :resolve_pjdefine "%~1"
if not defined AX_SRC call :resolve_fallback

if not defined AX_VER set "AX_VER=UNKNOWN"
echo [PostPackage] Layout source    : %AX_SRC%
echo [PostPackage] Software version : %AX_VER%

rem ---- compose the output folder -------------------------------------------
set "HAS_VARIANT=1"
if "%AX_VARIANT%"=="." set "HAS_VARIANT=0"
set "FLAT=0"
if "%AX_VERDIR%"=="." set "FLAT=1"

set "VARIANT_DIR=..\Debug"
if "%HAS_VARIANT%"=="1" set "VARIANT_DIR=..\Debug\%AX_VARIANT%"
if "%FLAT%"=="1" (
    set "OUTPUT_DIR=%VARIANT_DIR%"
    set "ROM_DIR=rom_%AX_VER%"
) else (
    set "OUTPUT_DIR=%VARIANT_DIR%\%AX_VERDIR%"
    set "ROM_DIR=rom_%AX_VERDIR%"
)

rem  guard : without a variant folder VARIANT_DIR is Debug itself. Never wipe
rem  it - the object tree (Application\ Generated\ Static_Code\) lives there.
if "%HAS_VARIANT%"=="0" if "%FLAT%"=="1" (
    echo [PostPackage] [WARNING] both axes are off - artifacts stay in Debug\.
    echo [PostPackage] [WARNING] Debug\ is NOT cleaned to protect the object tree.
)
if "%HAS_VARIANT%"=="1" if "%FLAT%"=="1" (
    rem flat layout: one build per variant folder -> rebuild the whole folder
    if exist "%VARIANT_DIR%" rmdir /s /q "%VARIANT_DIR%"
)
if "%HAS_VARIANT%"=="1" if "%FLAT%"=="0" (
    rem old flat layout: files and rom_* folders directly under VARIANT_DIR
    if exist "%VARIANT_DIR%\" (
        del /q "%VARIANT_DIR%\*.*" > nul 2> nul
        for /d %%D in ("%VARIANT_DIR%\rom_*") do rmdir /s /q "%%D"
    )
)
rem  same version -> rebuild only this version folder
if "%FLAT%"=="0" if not "%OUTPUT_DIR%"=="..\Debug" if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
echo [PostPackage] Output folder    : %OUTPUT_DIR%

rem ---- rename target : only meaningful when a variant names the model ------
set "NEW_BASE_NAME=%ORIGINAL_BASE_NAME%"
if "%HAS_VARIANT%"=="1" call :mk_newbase

rem ---- 5) build warning report (optional) ----------------------------------
if exist "%BUILDWARNING_EXE%" (
    echo [PostPackage] Generating build warning report...
    cd ..
    call "%BUILDWARNING_EXE%"
    cd Build
    if exist "..\Debug\*BuildWarning.xlsx" move "..\Debug\*BuildWarning.xlsx" "%OUTPUT_DIR%\" > nul
) else (
    echo [PostPackage] BuildWarning exe not found - skipping warning report.
)

rem ---- 6) move artifacts ---------------------------------------------------
echo [PostPackage] Moving artifacts to %OUTPUT_DIR% ...
for %%E in (sre elf hex map) do (
    if exist "..\Debug\%ORIGINAL_BASE_NAME%.%%E" move "..\Debug\%ORIGINAL_BASE_NAME%.%%E" "%OUTPUT_DIR%\" > nul
)
if exist "..\Debug\*.s19" move "..\Debug\*.s19" "%OUTPUT_DIR%\" > nul 2> nul

rem ---- 7) rename to model based name ---------------------------------------
if not "%NEW_BASE_NAME%"=="%ORIGINAL_BASE_NAME%" (
    echo [PostPackage] Renaming artifacts to %NEW_BASE_NAME% ...
    pushd "%OUTPUT_DIR%" > nul
    ren "%ORIGINAL_BASE_NAME%.*" "%NEW_BASE_NAME%.*" > nul
    if exist "%ORIGINAL_BASE_NAME%_Writing.s19" ren "%ORIGINAL_BASE_NAME%_Writing.s19" "%NEW_BASE_NAME%_Writing.s19" > nul
    popd > nul
)

rem ---- 8) rom_<version> package (aSIMS sign input) -------------------------
rem  only when the rom image was built (FBL Build.bat makes no .s19 -> skipped)
set "ROM_S19=%PKG_ROM_S19%"
if not defined ROM_S19 set "ROM_S19=%NEW_BASE_NAME%.s19"
set "HAS_S19=0"
if exist "%OUTPUT_DIR%\%ROM_S19%" set "HAS_S19=1"
if "%HAS_S19%"=="0" echo [PostPackage] No %ROM_S19% - rom package skipped.
if "%HAS_S19%"=="1" if not "%AX_VER%"=="UNKNOWN" (
    echo [PostPackage] Packaging for version %AX_VER% ...
    pushd "%OUTPUT_DIR%" > nul
    if not exist "%ROM_DIR%" mkdir "%ROM_DIR%"
    copy "%ROM_S19%" "%ROM_DIR%\" > nul
    if exist "%SECUREFLASH_INI%" (
        copy "%SECUREFLASH_INI%" "%ROM_DIR%\" > nul
    ) else (
        echo [PostPackage] [WARNING] SecureFlash ini not found - looked for References\*Signed_Firmware*\*.ini. Set SECUREFLASH_INI in the hook to override.
    )
    echo [PostPackage] Create zip file : %ROM_DIR%.zip
    tar -a -cf "%ROM_DIR%.zip" "%ROM_DIR%"
    popd > nul
)

echo [PostPackage] Finished %AX_SRC% version %AX_VER% -^> %OUTPUT_DIR%
goto :done

rem ==========================================================================
rem  (c) literal declaration : "<variant> <verdir> <version>"
rem ==========================================================================
:resolve_literal
for /f "usebackq tokens=1,2,3" %%a in ('%PKG_FOLDER%') do (
    set "AX_VARIANT=%%a"
    set "AX_VERDIR=%%b"
    set "AX_VER=%%c"
)
if not defined AX_VERDIR (
    echo [PostPackage] [WARNING] PKG_FOLDER needs 3 tokens : "<variant> <verdir> <version>"
    set "AX_VARIANT="
    goto :eof
)
set "AX_SRC=PKG_FOLDER"
goto :eof

rem ==========================================================================
rem  (b) version only - one capture group out of any file, no variant axis
rem ==========================================================================
:resolve_version
if not defined PKG_VERSION_PATTERN (
    echo [PostPackage] [WARNING] PKG_VERSION_FILE set without PKG_VERSION_PATTERN.
    goto :eof
)
if not exist "%PKG_VERSION_FILE%" (
    echo [PostPackage] [WARNING] PKG_VERSION_FILE not found : %PKG_VERSION_FILE%
    goto :eof
)
for /f "usebackq delims=" %%v in (`%PS% -Command "$m=[regex]::Match([IO.File]::ReadAllText($env:PKG_VERSION_FILE),$env:PKG_VERSION_PATTERN); if ($m.Success -and $m.Groups.Count -gt 1) { $m.Groups[1].Value }"`) do set "AX_VER=%%v"
if not defined AX_VER (
    echo [PostPackage] [WARNING] PKG_VERSION_PATTERN matched nothing in %PKG_VERSION_FILE%
    goto :eof
)
set "AX_VARIANT=."
set "AX_VERDIR=%AX_VER%"
set "AX_SRC=PKG_VERSION_FILE"
goto :eof

rem ==========================================================================
rem  (a) resolver - PJ_Define.h, both axes decided by PJ_Variant.ps1
rem ==========================================================================
:resolve_pjdefine
if not exist "%PKG_RESOLVER_FILE%" (
    echo [PostPackage] [WARNING] PKG_RESOLVER_FILE not found : %PKG_RESOLVER_FILE%
    goto :eof
)
if not exist "%SCRIPT_DIR%PJ_Variant.ps1" (
    echo [PostPackage] [WARNING] PJ_Variant.ps1 not found next to this script.
    goto :eof
)
rem  variant : arg1 from BuildVariants.bat, else the enabled OEUK option.
rem  no regex anchor here on purpose - TrimStart/StartsWith cannot be defused
rem  by cmd caret handling, and a commented out option must never be picked.
set "VARIANT=%~1"
if not defined VARIANT (
    for /f "usebackq delims=" %%i in (`%PS% -Command "foreach ($l in [IO.File]::ReadAllLines($env:PKG_RESOLVER_FILE)) { $s = $l.TrimStart(); if ($s.StartsWith('#define')) { $m = [regex]::Match($s, '#define[ \t]+(OEUK_\w+)'); if ($m.Success) { $m.Groups[1].Value } } }"`) do (
        if not defined VARIANT set "VARIANT=%%i"
    )
)
if not defined VARIANT (
    echo [PostPackage] [WARNING] no enabled OEUK option in %PKG_RESOLVER_FILE%
    goto :eof
)
echo [PostPackage] Target variant   : %VARIANT%
for /f "usebackq tokens=1,2,3" %%a in (`%PS% -File "%SCRIPT_DIR%PJ_Variant.ps1" -Action folder -File "%PKG_RESOLVER_FILE%" -Variant %VARIANT%`) do (
    if not defined AX_VARIANT (
        set "AX_VARIANT=%%a"
        set "AX_VERDIR=%%b"
        set "AX_VER=%%c"
    )
)
if "%AX_VARIANT%"=="[PJ_Variant]" (
    echo [PostPackage] [WARNING] PJ_Variant.ps1 error - see the line above.
    set "AX_VARIANT="
    set "AX_VERDIR="
    set "AX_VER="
    goto :eof
)
if defined AX_VARIANT set "AX_SRC=PKG_RESOLVER_FILE"
goto :eof

rem ==========================================================================
rem  fallback - never skip. The artifact name carries a version token.
rem ==========================================================================
:resolve_fallback
for /f "usebackq delims=" %%v in (`%PS% -Command "$m = [regex]::Match($env:PKG_BASENAME, '_(v[0-9][0-9_]*)$'); if ($m.Success) { $m.Groups[1].Value }"`) do set "AX_VER=%%v"
if not defined AX_VER set "AX_VER=UNKNOWN"
set "AX_VARIANT=."
set "AX_VERDIR=%AX_VER%"
set "AX_SRC=FALLBACK"
echo [PostPackage] ==========================================================
echo [PostPackage] [WARNING] packaging layout could not be resolved.
echo [PostPackage] [WARNING] Falling back to Debug\%AX_VER%\ - that version
echo [PostPackage] [WARNING] comes from the artifact name, not the project.
echo [PostPackage] [WARNING] Declare PKG_RESOLVER_FILE or PKG_VERSION_FILE
echo [PostPackage] [WARNING] in Build_Hook_^<MODEL^>.bat for the real layout.
echo [PostPackage] ==========================================================
goto :eof

rem ==========================================================================
rem  model based artifact name : he1i_psu_app_v3_0_29 from OEUK_HE1I
rem ==========================================================================
:mk_newbase
set "PKG_PREFIX=%AX_VARIANT:OEUK_=%"
set "PKG_PREFIX=%PKG_PREFIX:_TEST=%"
for /f "usebackq delims=" %%p in (`%PS% -Command "$env:PKG_PREFIX.ToLower()"`) do set "PREFIX_LOWER=%%p"
rem  Every known project already builds the model into the artifact name, for
rem  the base AND the TEST variant - verified 2026-11-13: psu_app 26810\ and
rem  26810_test\ both hold he1i_psu_app_v3_0_29.*, psu_fbl OEUK_HE1I\ and
rem  OEUK_HE1I_TEST\ both he1i_psu_fbl_v3_0_19.*, tpms FBL OEUK_LT2\ and
rem  OEUK_LT2_TEST\ both e_lt2_tpms_asr_swp_fbl_v2110.*. So the rename is a
rem  no-op in every real case and must NOT fire when the first token is not
rem  the model : e_lt2_tpms_asr_swp_fbl would become lt2_lt2_tpms_asr_swp_fbl.
rem  Rename only when the model is absent from the name - the case the rule
rem  was written for (a TEST build whose binary is named after TEST).
set "PKG_WANT=%PREFIX_LOWER%"
set "HAS_MODEL=no"
for /f "usebackq delims=" %%h in (`%PS% -Command "if ((($env:PKG_BASENAME).ToLower() -split '_') -contains $env:PKG_WANT) { 'yes' } else { 'no' }"`) do set "HAS_MODEL=%%h"
if "%HAS_MODEL%"=="yes" goto :eof
for /f "tokens=1,* delims=_" %%a in ("%ORIGINAL_BASE_NAME%") do set "SUFFIX=_%%b"
set "NEW_BASE_NAME=%PREFIX_LOWER%%SUFFIX%"
goto :eof

:done
endlocal
exit /b 0
