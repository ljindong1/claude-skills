@echo off
REM eCoDY-ECM daily change monitoring - unattended run.
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

if not defined ECODY_ECM_MONITOR_HOME set "ECODY_ECM_MONITOR_HOME=D:\Ljindong\automation\ecody-ecm-monitor"

if not exist "%ECODY_ECM_MONITOR_HOME%" (
  echo [FAIL] working folder not found: "%ECODY_ECM_MONITOR_HOME%"
  exit /b 9
)

cd /d "%ECODY_ECM_MONITOR_HOME%" || exit /b 9

REM The ECM API token lives in the user environment. Task Scheduler normally
REM hands it over, but read it from the registry if it is missing.
if not defined ECODY_ECM_TOKEN (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('ECODY_ECM_TOKEN','User')"`) do set "ECODY_ECM_TOKEN=%%i"
)
if not defined ECODY_ECM_TOKEN (
  echo [FAIL] ECODY_ECM_TOKEN is not set. Re-register it with setx.
  exit /b 8
)

REM The %date% format is locale dependent. Build the log name with PowerShell.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM"') do set YM=%%i
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set NOW=%%i

if not exist logs mkdir logs
set LOG=logs\run-%YM%.log

echo.>> "%LOG%"
echo ===== %NOW% RUN START =====>> "%LOG%"

claude -p "/ecody-ecm-monitor" ^
  --permission-mode acceptEdits ^
  --allowedTools "Bash(python *),PowerShell(python *),Read,Write,ToolSearch,mcp__claude_ai_Atlassian__getConfluencePageDescendants,mcp__claude_ai_Atlassian__getConfluencePage,mcp__claude_ai_Atlassian__createConfluencePage,mcp__claude_ai_Atlassian__updateConfluencePage,mcp__claude_ai_Atlassian__getContentFormatGuide" ^
  --permission-prompts none ^
  --output-format json >> "%LOG%" 2>&1

set RC=%ERRORLEVEL%
echo ===== EXIT CODE %RC% =====>> "%LOG%"

REM A non-zero code is an incident. Usual causes: ECM token expiry (2027-03),
REM MCP OAuth expiry, no intranet. The skill publishes its own failure page
REM when it can reach Confluence but not eCoDY-ECM.
if not "%RC%"=="0" (
  echo [FAIL] ECM monitor run failed ^(code %RC%^). See %LOG%.
  powershell -NoProfile -Command "[Console]::Beep(800,300)" >nul 2>&1
)

exit /b %RC%
