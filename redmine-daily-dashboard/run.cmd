@echo off
REM Redmine daily dashboard - unattended run.
REM
REM This file lives in the SKILL folder (version controlled in skills-repo).
REM The working folder (state/, logs/) is a different place - see below.
REM
REM Task Scheduler: Program = this file. "Start in" does not matter;
REM this script cd's to the working folder itself.
REM
REM NOTE: keep this file ASCII-only with CRLF line endings.
REM       cmd.exe reads batch files in the ANSI codepage (949) and
REM       chokes on LF-only line endings. Korean text here breaks it.

setlocal

REM Working folder: env var wins, else the default. Same rule as collect.py.
if not defined REDMINE_DASHBOARD_HOME set "REDMINE_DASHBOARD_HOME=D:\Ljindong\automation\redmine-dashboard"

if not exist "%REDMINE_DASHBOARD_HOME%\state" (
  echo [FAIL] working folder not found: "%REDMINE_DASHBOARD_HOME%"
  exit /b 9
)

cd /d "%REDMINE_DASHBOARD_HOME%" || exit /b 9

REM %date% format is locale dependent. Build the log name with PowerShell.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM"') do set YM=%%i
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set NOW=%%i

if not exist logs mkdir logs
set LOG=logs\run-%YM%.log

echo.>> "%LOG%"
echo ===== %NOW% RUN START =====>> "%LOG%"

claude -p "/redmine-daily-dashboard" ^
  --permission-mode acceptEdits ^
  --allowedTools "Bash(python *),Read,Write,mcp__claude_ai_Atlassian__getConfluencePage,mcp__claude_ai_Atlassian__updateConfluencePage" ^
  --permission-prompts none ^
  --output-format json >> "%LOG%" 2>&1

set RC=%ERRORLEVEL%
echo ===== EXIT CODE %RC% =====>> "%LOG%"

REM A non-zero code is an incident. Usual causes: MCP OAuth expiry, no intranet.
if not "%RC%"=="0" (
  echo [FAIL] dashboard run failed ^(code %RC%^). See %LOG%.
  powershell -NoProfile -Command "[Console]::Beep(800,300)" >nul 2>&1
)

exit /b %RC%
