# 주간 자동 동기화를 Windows 작업 스케줄러에 등록한다 (기본: 매주 금요일 17:00).
#
#   등록:  .\install_weekly_task.ps1
#   시간 바꾸기:  .\install_weekly_task.ps1 -At 18:30 -Day Thursday
#   지우기:  .\install_weekly_task.ps1 -Remove
#
# 돌리는 것은 weekly_sync.ps1 이고 sync 까지만 한다 (푸시는 사람이 승인한다).
param(
    [string]$At = '17:00',
    [string]$Day = 'Friday',
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$taskName = 'joule-repo-sync weekly'
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$script = Join-Path $here 'weekly_sync.ps1'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "작업을 지웠다: $taskName"
    exit 0
}

if (-not (Test-Path $script)) { throw "weekly_sync.ps1 을 찾지 못했다: $script" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $script)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $At
# 노트북이라 그 시각에 꺼져 있을 수 있다 - 놓치면 다음에 켤 때 돌고, 배터리로도 돈다.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Force `
    -Description 'joule 회사 저장소의 새 커밋을 개인 GitHub 사본 브랜치에 쌓는다 (푸시는 하지 않는다).' | Out-Null

"등록했다: $taskName  ($Day $At)"
"  돌리는 것: $script"
"  로그: $env:LOCALAPPDATA\joule-repo-sync\weekly.log"
