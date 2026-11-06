@echo off
REM eCoDY-IMS patch ticket monitoring - unattended run.
REM
REM This file lives in the SKILL folder (version controlled in skills-repo).
REM The working folder (logs/) is a different place - see below.
REM
REM Task Scheduler: Program = wscript.exe, Arguments = run-hidden.vbs
REM   Do NOT point the task at this file directly. Under an Interactive
REM   logon cmd.exe draws a console window, and because everything below
REM   is redirected to the log the window stays blank for several minutes.
REM   It looks hung, and closing it KILLS the run. run-hidden.vbs launches
REM   this script with no window at all and passes the exit code back.
REM   Start-in does not matter; this script changes folder itself.
REM
REM NOTE: keep this file ASCII-only with CRLF line endings.
REM       cmd.exe reads batch files in the ANSI codepage (949) and
REM       chokes on LF-only line endings. Korean text here breaks it.

setlocal

if not defined ECODY_IMS_MONITOR_HOME set "ECODY_IMS_MONITOR_HOME=D:\Ljindong\automation\ecody-ims-patch-monitor"

REM The skill folder, and the skills root that holds the sibling
REM ecody-search scripts this skill calls. %~dp0 keeps the trailing slash.
set "SKILL_DIR=%~dp0"
set "SKILLS_ROOT=%~dp0.."

if not exist "%ECODY_IMS_MONITOR_HOME%" mkdir "%ECODY_IMS_MONITOR_HOME%"
if not exist "%ECODY_IMS_MONITOR_HOME%" (
  echo [FAIL] working folder not found: "%ECODY_IMS_MONITOR_HOME%"
  exit /b 9
)

cd /d "%ECODY_IMS_MONITOR_HOME%" || exit /b 9

REM This skill reads BOTH sites: IMS for the tickets, ECM for the guides.
REM Task Scheduler normally hands the user environment over, but read it
REM from the registry if a token is missing.
if not defined ECODY_IMS_TOKEN (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('ECODY_IMS_TOKEN','User')"`) do set "ECODY_IMS_TOKEN=%%i"
)
if not defined ECODY_ECM_TOKEN (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('ECODY_ECM_TOKEN','User')"`) do set "ECODY_ECM_TOKEN=%%i"
)
if not defined ECODY_IMS_TOKEN (
  echo [FAIL] ECODY_IMS_TOKEN is not set. Re-register it with setx.
  exit /b 8
)
if not defined ECODY_ECM_TOKEN (
  echo [WARN] ECODY_ECM_TOKEN is not set. ECM guides will be skipped.
)

REM The %date% format is locale dependent. Build the log name with PowerShell.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM"') do set YM=%%i
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set NOW=%%i

if not exist logs mkdir logs
set LOG=logs\run-%YM%.log
set FULLLOG=%ECODY_IMS_MONITOR_HOME%\%LOG%

REM ---------------------------------------------------------------
REM Say what this is. Normally nobody sees this - the scheduled task
REM runs through run-hidden.vbs and draws no window. It shows only when
REM somebody starts run.cmd by hand, and then a blank window would be
REM a mystery worth closing. So explain, and warn against closing.
REM ---------------------------------------------------------------
title eCoDY IMS patch monitor - RUNNING - do not close
echo.
echo  ==============================================================
echo   eCoDY-IMS patch ticket monitor
echo  ==============================================================
echo   started   : %NOW%
echo   takes     : about 5-10 minutes
echo   log file  : %FULLLOG%
echo.
echo   Progress is written to the log, NOT to this window - so this
echo   window stays quiet until the run ends. That is normal.
echo.
echo   *** DO NOT CLOSE THIS WINDOW. Closing it kills the run. ***
echo.
echo   To watch it live, open another window and run:
echo     powershell -Command "Get-Content '%FULLLOG%' -Tail 30 -Wait"
echo  ==============================================================
echo.

echo.>> "%LOG%"
echo ===== %NOW% RUN START =====>> "%LOG%"

REM Runs AFTER the ECM monitor (09:00) so the intranet is already proven up.
REM
REM --add-dir: the working folder is the automation folder, so without this
REM   the skill cannot read its own references/page-format.md and the
REM   ecody-search scripts it calls. Both the repo path and the junction
REM   path are given because the skill may resolve to either.
REM
REM createConfluencePage is required: new patch tickets get a new page, and
REM every run writes one daily record page that carries the window marker.
REM searchConfluenceUsingCql finds the window marker in one call instead of
REM opening candidate pages one by one.
claude -p "/ecody-ims-patch-monitor" ^
  --permission-mode acceptEdits ^
  --add-dir "%SKILLS_ROOT%" ^
  --add-dir "%USERPROFILE%\.claude\skills" ^
  --allowedTools "Bash(python *),PowerShell(python *),Read,Write,Glob,Grep,ToolSearch,mcp__claude_ai_Atlassian__getConfluencePageDescendants,mcp__claude_ai_Atlassian__getConfluencePage,mcp__claude_ai_Atlassian__searchConfluenceUsingCql,mcp__claude_ai_Atlassian__createConfluencePage,mcp__claude_ai_Atlassian__updateConfluencePage,mcp__claude_ai_Atlassian__getContentFormatGuide" ^
  --permission-prompts none ^
  --output-format json >> "%LOG%" 2>&1

set RC=%ERRORLEVEL%
echo ===== EXIT CODE %RC% =====>> "%LOG%"

REM A non-zero code is an incident. Usual causes: token expiry (2027-03),
REM MCP OAuth expiry, no intranet. When the skill can reach Confluence but
REM not eCoDY it still writes the PATCH-INDEX area so the miss is visible.
if not "%RC%"=="0" (
  echo [FAIL] IMS patch monitor run failed ^(code %RC%^). See %FULLLOG%.
  powershell -NoProfile -Command "[Console]::Beep(800,300)" >nul 2>&1
) else (
  echo [OK] done. See %FULLLOG%
)

exit /b %RC%
