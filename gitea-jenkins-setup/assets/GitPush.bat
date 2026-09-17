@echo off
rem ==========================================================================
rem  GitPush.bat  -  commit and push build outputs (SW Platform LAB standard)
rem --------------------------------------------------------------------------
rem  Location : <project folder>\Build\   (same folder as Build_Hook_GIT_ASEC.bat)
rem  Called by: Build_Hook_GIT_ASEC.bat (only when the build succeeded)
rem  Edit     : [USER] section only
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion

rem ---- [USER] commit author : edit per user ---------------------------------
set "COMMIT_NAME=<Gitea display name>"
set "COMMIT_EMAIL=<company email>"

rem ---- [OPTION] fixed push branch : leave empty to use Jenkins GIT_BRANCH ----
set "PUSH_BRANCH="

rem ---- commit message : must match Jenkins "Polling ignores commits" filter -
set "COMMIT_MSG=Auto commit from Jenkins"

rem ---- check [USER] section -------------------------------------------------
if "!COMMIT_NAME:~0,1!"=="<"  goto :need_edit
if "!COMMIT_EMAIL:~0,1!"=="<" goto :need_edit

rem ---- repository root ------------------------------------------------------
if defined WORKSPACE (
    set "REPO_DIR=%WORKSPACE%"
) else (
    for /f "delims=" %%R in ('git -C "%~dp0." rev-parse --show-toplevel') do set "REPO_DIR=%%R"
)
cd /d "!REPO_DIR!" || (echo [GitPush] cannot move to repository root & exit /b 11)

rem ---- push branch : Jenkins gives GIT_BRANCH=origin/<branch> ---------------
if not defined PUSH_BRANCH if defined GIT_BRANCH set "PUSH_BRANCH=!GIT_BRANCH!"
if defined PUSH_BRANCH set "PUSH_BRANCH=!PUSH_BRANCH:origin/=!"
if not defined PUSH_BRANCH (
    echo [GitPush] push branch unknown - set PUSH_BRANCH or run from Jenkins
    exit /b 13
)
rem  safety : push only to devel_* work branches (never develop / main)
if /i not "!PUSH_BRANCH:~0,6!"=="devel_" (
    echo [GitPush] refuse to push to "!PUSH_BRANCH!" - only devel_* branches allowed
    exit /b 14
)

echo [GitPush] repository : !REPO_DIR!
echo [GitPush] branch     : !PUSH_BRANCH!

rem ---- commit ---------------------------------------------------------------
git config user.name "!COMMIT_NAME!"
git config user.email "!COMMIT_EMAIL!"

git add -f .
if errorlevel 1 (echo [GitPush] git add failed & exit /b 21)

git diff --cached --quiet
if not errorlevel 1 (
    echo [GitPush] no changes to commit - skip push
    exit /b 0
)

git commit -q -m "!COMMIT_MSG! #%BUILD_NUMBER%"
if errorlevel 1 (echo [GitPush] git commit failed & exit /b 22)

rem ---- push -----------------------------------------------------------------
git push origin HEAD:refs/heads/!PUSH_BRANCH!
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" echo [GitPush] git push failed - RC=!RC! : check build account write permission, or pull and push again
exit /b !RC!

:need_edit
echo [GitPush] edit COMMIT_NAME and COMMIT_EMAIL in GitPush.bat first
exit /b 12
