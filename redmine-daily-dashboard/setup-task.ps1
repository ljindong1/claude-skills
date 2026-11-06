# Redmine 일일 대시보드 - 예약 작업 교체 (실행 방식 + 시각)
#
# 실행:  powershell -NoProfile -ExecutionPolicy Bypass -File "<이 파일>"
#
# 무엇을 고치나 (2026-11-06, 11월 실행 이력 5회 중 2회 실패를 보고 정했다)
#
#   ① 실행 대상  run.cmd 직접  ->  wscript.exe run-hidden.vbs
#      빈 콘솔 창이 몇 분씩 떠 있으면 멈춘 줄 알고 닫게 되고, 닫으면 실행이 죽는다.
#      11-02 09:04 회차가 그렇게 죽었다 - 로그에 RUN START 한 줄 쓰고 0 바이트.
#
#   ② 트리거      평일 01:00  ->  평일 10:00
#      11-05 01:00 회차는 api_error 에 토큰 0, 비용 0 이었다. 요청이 아예 안 나갔다.
#      새벽에는 사내망.DNS 가 아직 안 올라온다. ECM 도 같은 이유로 09:00 으로 옮겼다.
#      실제 시작 시각이 01:00.03:25.03:35.09:04 로 제각각이던 것도 같이 없어진다
#      (PC 가 꺼져 있다가 깨어날 때 따라 돌던 것).
#
#   재시도는 넣지 않는다(사용자 방침 2026-11-06). 주원인이 시각이었고,
#   워치독이 실패를 잡아 알려 주므로 그때 수동으로 다시 돌린다.
#
# ⚠️ 워치독 '예약 실행 점검' 은 10:00 이라 이대로면 Redmine 을 판정할 수 없다.
#    watchdog\register_task.ps1 을 다시 돌려 11:00 으로 옮겨야 한다.
#
# 이 파일은 UTF-8 BOM 으로 저장해야 한다 - PowerShell 5.1 은 BOM 이 없으면
# .ps1 을 ANSI 로 읽어 한글 작업 이름이 깨진다.

$ErrorActionPreference = 'Stop'

$TaskName = 'Redmine 일일 대시보드'
$At       = '10:00'
$Launcher = Join-Path $PSScriptRoot 'run-hidden.vbs'
$RunCmd   = Join-Path $PSScriptRoot 'run.cmd'
$WorkHome = 'D:\Ljindong\automation\redmine-dashboard'

foreach ($f in @($Launcher, $RunCmd)) {
    if (-not (Test-Path $f)) {
        Write-Host "[FAIL] 파일이 없습니다: $f" -ForegroundColor Red
        exit 9
    }
}
if (-not (Test-Path (Join-Path $WorkHome 'state'))) {
    Write-Host "[FAIL] 작업 폴더가 없습니다: $WorkHome\state" -ForegroundColor Red
    Write-Host "       run.cmd 도 이 폴더가 없으면 코드 9 로 끝납니다."
    exit 9
}

$action = New-ScheduledTaskAction -Execute 'wscript.exe' `
    -Argument ('"' + $Launcher + '"') -WorkingDirectory $WorkHome

$trigger = New-ScheduledTaskTrigger -Weekly -At $At `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($null -eq $existing) {
    Write-Host "[FAIL] '$TaskName' 작업이 없습니다. 이 스크립트는 교체 전용입니다." -ForegroundColor Red
    exit 3
}
if ($existing.State -eq 'Running') {
    Write-Host "[FAIL] 지금 실행 중입니다. 끝난 뒤에 다시 시도하세요." -ForegroundColor Red
    exit 2
}

$beforeAct = '{0} {1}' -f $existing.Actions[0].Execute, $existing.Actions[0].Arguments
$beforeTrg = $existing.Triggers[0].StartBoundary

Write-Host "[..]   실행 대상과 트리거를 바꿉니다 (설정.계정은 그대로)"
Write-Host "       전 실행   : $beforeAct"
Write-Host "       전 트리거 : $beforeTrg"

Set-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName
$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "       후 실행   : $($t.Actions[0].Execute) $($t.Actions[0].Arguments)"
Write-Host "       후 트리거 : $($t.Triggers[0].StartBoundary)"
Write-Host ""
Write-Host "[OK]   교체 완료 - 창 없이, 평일 $At 에 돕니다" -ForegroundColor Green
Write-Host "       다음 실행 : $($i.NextRunTime)"
Write-Host ""
Write-Host "다음에 할 일: 워치독을 11:00 으로 옮깁니다" -ForegroundColor Yellow
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File ""D:\Ljindong\skills-repo\watchdog\register_task.ps1"""
Write-Host ""
Write-Host "지금 한 번 돌려 보려면:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "진행 상황 보기:          Get-Content '$WorkHome\logs\run-<yyyy-MM>.log' -Tail 20 -Wait"
