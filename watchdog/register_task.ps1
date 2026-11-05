# "예약 실행 점검" 작업을 윈도 작업 스케줄러에 등록한다. 한 번만 실행하면 된다.
# 실행: powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Ljindong\skills-repo\watchdog\register_task.ps1"

$ErrorActionPreference = 'Stop'

$script = 'D:\Ljindong\skills-repo\watchdog\check_runs.ps1'
if (-not (Test-Path -LiteralPath $script)) { throw "점검 스크립트가 없습니다: $script" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $script + '"')

$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At '10:00'

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName '예약 실행 점검' `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description 'eCoDY ECM / Redmine 예약 실행이 실제로 돌았는지 확인하고, 안 돌았거나 실패했으면 보고서를 띄운다.' `
    -Force | Out-Null

$t = Get-ScheduledTask -TaskName '예약 실행 점검'
$i = Get-ScheduledTaskInfo -TaskName '예약 실행 점검'
Write-Output ('등록 완료: 상태 ' + $t.State + ' / 다음 실행 ' + $i.NextRunTime)
Write-Output '지금 바로 시험해 보려면: Start-ScheduledTask -TaskName "예약 실행 점검"'
