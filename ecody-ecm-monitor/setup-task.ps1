# eCoDY ECM 일일 모니터링 - 예약 작업 등록 / 실행 방식 교체
#
# 실행:  powershell -NoProfile -ExecutionPolicy Bypass -File "<이 파일>"
#
#   작업이 없으면  -> 평일 09:00 로 새로 등록한다
#   작업이 있으면  -> **실행 대상(Action)만** run-hidden.vbs 로 바꾼다.
#                     트리거.설정.계정은 손대지 않는다
#
# run.cmd 를 직접 부르지 않고 run-hidden.vbs 를 거치는 이유:
#   콘솔 창이 빈 화면으로 몇 분씩 떠 있으면 멈춘 줄 알고 닫게 되고,
#   닫으면 실행이 죽는다. 이 방식은 창이 아예 뜨지 않는다.
#
# 이 파일은 UTF-8 BOM 으로 저장해야 한다 - PowerShell 5.1 은 BOM 이 없으면
# .ps1 을 ANSI 로 읽어 한글 작업 이름이 깨진다.

$ErrorActionPreference = 'Stop'

$TaskName = 'eCoDY ECM 일일 모니터링'
$Launcher = Join-Path $PSScriptRoot 'run-hidden.vbs'
$RunCmd   = Join-Path $PSScriptRoot 'run.cmd'
$WorkHome = 'D:\Ljindong\automation\ecody-ecm-monitor'

foreach ($f in @($Launcher, $RunCmd)) {
    if (-not (Test-Path $f)) {
        Write-Host "[FAIL] 파일이 없습니다: $f" -ForegroundColor Red
        exit 9
    }
}

if (-not (Test-Path $WorkHome)) {
    New-Item -ItemType Directory -Force -Path $WorkHome | Out-Null
    Write-Host "[OK]   작업 폴더 생성: $WorkHome"
}

# wscript.exe 로 숨겨 실행한다. 창이 전혀 뜨지 않는다.
$action = New-ScheduledTaskAction -Execute 'wscript.exe' `
    -Argument ('"' + $Launcher + '"') -WorkingDirectory $WorkHome

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($null -ne $existing) {

    $before = $existing.Actions[0]
    if ($before.Execute -eq 'wscript.exe') {
        Write-Host "[SKIP] 이미 창 없이 실행하도록 되어 있습니다." -ForegroundColor Yellow
        exit 0
    }
    if ($existing.State -eq 'Running') {
        Write-Host "[FAIL] 지금 실행 중입니다. 끝난 뒤에 다시 시도하세요." -ForegroundColor Red
        Write-Host "       상태 보기:  Get-ScheduledTask -TaskName '$TaskName'"
        exit 2
    }

    Write-Host "[..]   실행 대상만 교체합니다 (트리거.설정은 그대로)"
    Write-Host "       전 : $($before.Execute) $($before.Arguments)"

    Set-ScheduledTask -TaskName $TaskName -Action $action | Out-Null

    $t = Get-ScheduledTask -TaskName $TaskName
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "       후 : $($t.Actions[0].Execute) $($t.Actions[0].Arguments)"
    Write-Host ""
    Write-Host "[OK]   교체 완료 - 이제 창 없이 돕니다" -ForegroundColor Green
    Write-Host "       트리거    : $($t.Triggers[0].StartBoundary)"
    Write-Host "       다음 실행 : $($i.NextRunTime)"

} else {

    $trigger = New-ScheduledTaskTrigger -Weekly -At '09:00' `
        -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday

    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
        -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal -Description 'eCoDY-ECM 변경분을 수집해 사내 Confluence 330366991 하위에 원장과 날짜별 기록으로 발행. 창 없이 돈다 - 진행 상황은 작업 폴더의 logs 를 본다.' | Out-Null

    $t = Get-ScheduledTask -TaskName $TaskName
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host ""
    Write-Host "[OK]   새로 등록 완료 (창 없이 실행)" -ForegroundColor Green
    Write-Host "       이름      : $($t.TaskName)"
    Write-Host "       다음 실행 : $($i.NextRunTime)"
}

Write-Host ""
Write-Host "지금 한 번 돌려 보려면:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "진행 상황 보기:          Get-Content '$WorkHome\logs\run-<yyyy-MM>.log' -Tail 20 -Wait"
