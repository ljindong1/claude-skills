# eCoDY-IMS 패치 모니터링 - 예약 작업 등록
#
# 실행:  powershell -NoProfile -ExecutionPolicy Bypass -File "<이 파일>"
#
# ECM 모니터링(09:00) 뒤인 09:30 평일에 run.cmd 를 돌린다.
# 프로그램은 스킬 폴더(저장소), 기록(logs)은 작업 폴더에 남는다.
# 이 파일은 UTF-8 BOM 으로 저장해야 한다 - PowerShell 5.1 은 BOM 이 없으면
# .ps1 을 ANSI 로 읽어 한글 작업 이름이 깨진다.

$ErrorActionPreference = 'Stop'

$TaskName = 'eCoDY IMS 패치 모니터링'
$RunCmd   = Join-Path $PSScriptRoot 'run.cmd'
$WorkHome = 'D:\Ljindong\automation\ecody-ims-patch-monitor'

if (-not (Test-Path $RunCmd)) {
    Write-Host "[FAIL] run.cmd 가 없습니다: $RunCmd" -ForegroundColor Red
    exit 9
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    Write-Host "[SKIP] 같은 이름의 작업이 이미 있습니다: $TaskName" -ForegroundColor Yellow
    Write-Host "       지우고 다시 만들려면:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
    exit 1
}

if (-not (Test-Path $WorkHome)) {
    New-Item -ItemType Directory -Force -Path $WorkHome | Out-Null
    Write-Host "[OK]   작업 폴더 생성: $WorkHome"
}

$action = New-ScheduledTaskAction -Execute $RunCmd -WorkingDirectory $WorkHome

$trigger = New-ScheduledTaskTrigger -Weekly -At '09:30' `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

$desc = 'eCoDY-IMS SWP Delivery_Patch 티켓을 추적해 사내 Confluence 334594056 하위에 정리. ' +
        '구간 내 신규 티켓은 페이지 생성, 기존 페이지는 변화 시 갱신, ' +
        '결과는 일별 기록(380698635 하위). ECM 모니터링(09:00) 뒤에 실행.'

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $desc | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName
$i = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host ""
Write-Host "[OK]   등록 완료" -ForegroundColor Green
Write-Host "       이름      : $($t.TaskName)"
Write-Host "       상태      : $($t.State)"
Write-Host "       프로그램  : $RunCmd"
Write-Host "       작업 폴더 : $WorkHome"
Write-Host "       다음 실행 : $($i.NextRunTime)"
Write-Host ""
Write-Host "지금 한 번 돌려 보려면:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "로그:                    $WorkHome\logs\run-<yyyy-MM>.log"
