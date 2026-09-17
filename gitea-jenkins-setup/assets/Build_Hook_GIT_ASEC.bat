@echo off
rem ==========================================================================
rem  Build_Hook_GIT_ASEC.bat  -  Jenkins entry batch (SW Platform LAB standard)
rem --------------------------------------------------------------------------
rem  Location : <project folder>\Build\   (same folder as Build.bat)
rem  Called by: Jenkins Job build command
rem             <project folder>\Build\Build_Hook_GIT_ASEC.bat %BuildType% -j8
rem  Steps    : 1) decide action  2) run Build.bat  3) check new .elf
rem             4) push outputs via GitPush.bat  5) return exit code
rem  Edit     : NOT required (paths and branch are detected automatically)
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion

rem ---- paths (automatic) ----------------------------------------------------
set "HOOK_DIR=%~dp0"
for %%I in ("%HOOK_DIR%..") do set "PROJ_DIR=%%~fI"
set "BUILD_RC=0"
set "PUSH_RC=0"

rem ---- 1) decide action -----------------------------------------------------
rem  arg1 : Hook | Build | Compile | GenerateAll | Rebuild | Clean
rem  Hook : use the last commit subject as the action (default Build)
set "param=%~1"
set "jopt=%~2"
if "%param%"=="" set "param=Hook"
echo With Parameter !param!

if /i "!param!"=="Hook" (
    set "param="
    for /f "usebackq delims=" %%L in (`git -C "%PROJ_DIR%" log -1 --pretty^=format:%%s`) do (
        if not defined param set "param=%%L"
    )
    echo gitLog !param!
)

set "result=Build"
set "known=0"
for %%K in (Build Compile GenerateAll Rebuild Clean) do if /i "!param!"=="%%K" set "known=1"
if "!known!"=="0" echo Invalid Parameter. Default "Build"
if /i "!param!"=="Compile"     set "result=Compile"
if /i "!param!"=="GenerateAll" set "result=GenerateAll"
if /i "!param!"=="Rebuild"     set "result=Rebuild"
if /i "!param!"=="Rebuild"     set "jopt=-j8"
if /i "!param!"=="Clean"       set "result=Build -c"

rem ---- 2) build -------------------------------------------------------------
echo run build with param: !result! !jopt!
set "MARKER=%TEMP%\hook_marker_%RANDOM%%RANDOM%.tmp"
type nul > "%MARKER%"
pushd "%PROJ_DIR%"
call Build\Build.bat !result! !jopt!
set "BUILD_RC=!ERRORLEVEL!"
popd

rem ---- 3) check new .elf (Build.bat exit code alone is not reliable) --------
if /i "!result!"=="Build -c"    goto :skip_check
if /i "!result!"=="GenerateAll" goto :skip_check
if /i "!result!"=="Compile"     goto :skip_check
powershell -NoProfile -Command "$m=(Get-Item -LiteralPath '%MARKER%').LastWriteTime; $e=Get-ChildItem -LiteralPath '%PROJ_DIR%' -Recurse -Filter *.elf -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $m }; if ($e) { $e | ForEach-Object { Write-Host ('[HOOK] New ELF : ' + $_.FullName) }; exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo [HOOK] No new .elf file - treated as build failure.
    if "!BUILD_RC!"=="0" set "BUILD_RC=9"
)
:skip_check

rem ---- 4) push outputs ------------------------------------------------------
if not "!BUILD_RC!"=="0" (
    echo [HOOK] Build failed - skip Git Push.
    goto :finish
)
if not exist "%HOOK_DIR%GitPush.bat" (
    echo [HOOK] GitPush.bat not found in %HOOK_DIR%
    set "PUSH_RC=8"
    goto :finish
)
call "%HOOK_DIR%GitPush.bat"
set "PUSH_RC=!ERRORLEVEL!"

rem ---- 5) result ------------------------------------------------------------
:finish
if exist "%MARKER%" del /q "%MARKER%"
set "FINAL_RC=0"
if not "!BUILD_RC!"=="0" set "FINAL_RC=!BUILD_RC!"
if "!FINAL_RC!"=="0" if not "!PUSH_RC!"=="0" set "FINAL_RC=!PUSH_RC!"
echo [HOOK] Build ERROR LEVEL : !BUILD_RC!
echo [HOOK] Git Push ERROR LEVEL : !PUSH_RC!
echo [HOOK] Final ERROR LEVEL : !FINAL_RC!
endlocal & exit /b %FINAL_RC%
