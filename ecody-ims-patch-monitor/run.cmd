@echo off
REM eCoDY-IMS patch ticket monitoring - unattended run.
REM
REM This file lives in the SKILL folder (version controlled in skills-repo).
REM The working folder (logs/) is a different place - see below.
REM
REM Task Scheduler: Program = this file. Start-in does not matter;
REM this script changes to the working folder itself.
REM
REM NOTE: keep this file ASCII-only with CRLF line endings.
REM       cmd.exe reads batch files in the ANSI codepage (949) and
REM       chokes on LF-only line endings. Korean text here breaks it.

setlocal

if not defined ECODY_IMS_MONITOR_HOME set "ECODY_IMS_MONITOR_HOME=D:\Ljindong\automation\ecody-ims-patch-monitor"

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

echo.>> "%LOG%"
echo ===== %NOW% RUN START =====>> "%LOG%"

REM Runs AFTER the ECM monitor (09:00) so the intranet is already proven up.
REM createConfluencePage is required: new patch tickets get a new page, and
REM every run writes one daily record page that carries the window marker.
claude -p "/ecody-ims-patch-monitor" ^
  --permission-mode acceptEdits ^
  --allowedTools "Bash(python *),PowerShell(python *),Read,Write,ToolSearch,mcp__claude_ai_Atlassian__getConfluencePageDescendants,mcp__claude_ai_Atlassian__getConfluencePage,mcp__claude_ai_Atlassian__createConfluencePage,mcp__claude_ai_Atlassian__updateConfluencePage,mcp__claude_ai_Atlassian__getContentFormatGuide" ^
  --permission-prompts none ^
  --output-format json >> "%LOG%" 2>&1

set RC=%ERRORLEVEL%
echo ===== EXIT CODE %RC% =====>> "%LOG%"

REM A non-zero code is an incident. Usual causes: token expiry (2027-03),
REM MCP OAuth expiry, no intranet. When the skill can reach Confluence but
REM not eCoDY it still writes the PATCH-INDEX area so the miss is visible.
if not "%RC%"=="0" (
  echo [FAIL] IMS patch monitor run failed ^(code %RC%^). See %LOG%.
  powershell -NoProfile -Command "[Console]::Beep(800,300)" >nul 2>&1
)

exit /b %RC%
