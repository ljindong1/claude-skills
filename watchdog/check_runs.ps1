# 예약 실행 점검 - 평일 아침 예약 작업이 실제로 돌았는지 확인하고, 안 돌았으면 알린다.
# 목적: PC 가 켜져 있는데도 실행이 빠지거나 죽은 경우를 사람이 모르고 지나치지 않게 한다.
# 이 스크립트는 Claude 를 쓰지 않는다 - 순수 PowerShell 이라 API/네트워크가 죽어도 동작한다.
# 호출: 작업 스케줄러 "예약 실행 점검" (평일 10:00)

[CmdletBinding()]
param(
    [switch]$NoPopup,   # 창을 띄우지 않고 보고서만 남긴다
    [switch]$Force      # 예정 시각 전이라도 판정한다 (수동 확인용)
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$Base = 'D:\Ljindong\automation'
$WatchDir = Join-Path $Base 'watchdog'
if (-not (Test-Path -LiteralPath $WatchDir)) {
    New-Item -ItemType Directory -Path $WatchDir -Force | Out-Null
}

# 점검 대상. Due 는 예약 시각(이 시각이 지나야 판정한다), Grace 는 그 뒤로 더 기다려 줄 분(실행 시간).
$Jobs = @(
    [pscustomobject]@{
        Label = 'eCoDY ECM 일일 모니터링'
        Task  = 'eCoDY ECM 일일 모니터링'
        LogDir = Join-Path $Base 'ecody-ecm-monitor\logs'
        Due   = '09:00'
        Grace = 45
    }

    [pscustomobject]@{
        Label = 'eCoDY IMS 패치 모니터링'
        Task  = 'eCoDY IMS 패치 모니터링'
        LogDir = Join-Path $Base 'ecody-ims-patch-monitor\logs'
        Due   = '09:30'
        Grace = 45
    }

    # Redmine 되살림 (2026-11-06). 11월 5회 중 2회가 실패였는데 점검 대상이 아니라
    # 아무도 몰랐다 - 11-02 는 콘솔 창이 닫혀 즉사(로그 0바이트), 11-05 는 새벽
    # 01:00 이라 사내망이 없어 api_error. 둘 다 고치면서 감시에 다시 넣는다.
    [pscustomobject]@{
        Label  = 'Redmine 일일 대시보드'
        Task   = 'Redmine 일일 대시보드'
        LogDir = Join-Path $Base 'redmine-dashboard\logs'
        Due    = '10:00'
        Grace  = 60
    }
)

$now = Get-Date
$todayStr = $now.ToString('yyyy-MM-dd')
$logName  = 'run-' + $now.ToString('yyyy-MM') + '.log'

$lines = New-Object System.Collections.Generic.List[string]
$problems = 0
$summary = New-Object System.Collections.Generic.List[string]

$lines.Add('예약 실행 점검  ' + $now.ToString('yyyy-MM-dd (ddd) HH:mm:ss'))
$lines.Add('컴퓨터: ' + $env:COMPUTERNAME + '   사용자: ' + $env:USERNAME)
$lines.Add('')

foreach ($j in $Jobs) {

    $state = ''
    $detail = ''
    $logPath = Join-Path $j.LogDir $logName

    # --- 작업 스케줄러가 보는 상태 ---
    $task = Get-ScheduledTask -TaskName $j.Task -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        $state = '작업 없음'
        $detail = '작업 스케줄러에 "' + $j.Task + '" 이(가) 등록돼 있지 않습니다.'
        $problems++
        $lines.Add('[' + $state + '] ' + $j.Label)
        $lines.Add('    ' + $detail)
        $lines.Add('')
        $summary.Add($j.Label + ': ' + $state)
        continue
    }
    $info = Get-ScheduledTaskInfo -TaskName $j.Task

    # --- 아직 판정할 때가 아닌가 ---
    $due = [datetime]::ParseExact($todayStr + ' ' + $j.Due, 'yyyy-MM-dd HH:mm', $null)
    $deadline = $due.AddMinutes($j.Grace)
    $isWeekday = ($now.DayOfWeek -ne 'Saturday') -and ($now.DayOfWeek -ne 'Sunday')

    if (-not $isWeekday -and -not $Force) {
        $lines.Add('[건너뜀] ' + $j.Label + ' - 오늘은 주말이라 예약이 없습니다.')
        $lines.Add('')
        continue
    }
    if ($now -lt $deadline -and -not $Force) {
        $lines.Add('[대기] ' + $j.Label + ' - 아직 판정 시각(' + $deadline.ToString('HH:mm') + ') 전입니다.')
        $lines.Add('')
        continue
    }

    # 오늘 예약을 새로 걸거나 시각을 바꾼 날은 판정하지 않는다.
    # 예약 시각이 지난 뒤에 등록하면 당연히 기록이 없고, 그것은 사고가 아니다.
    $startBoundary = $null
    try { $startBoundary = [datetime]($task.Triggers[0].StartBoundary) } catch { }
    if ($null -ne $startBoundary -and $startBoundary.Date -eq $now.Date -and -not $Force) {
        $lines.Add('[건너뜀] ' + $j.Label + ' - 오늘 예약을 등록·변경했습니다. 판정은 다음 회차부터.')
        $lines.Add('')
        continue
    }

    # --- 로그에서 오늘 회차를 찾는다 ---
    $startTime = ''
    $exitCode = $null
    $resultMsg = ''
    $hasToday = $false

    if (Test-Path -LiteralPath $logPath) {
        $log = @(Get-Content -LiteralPath $logPath -Encoding UTF8 -ErrorAction SilentlyContinue)
        $startIdx = -1
        # 머리글 모양을 정확히 맞춘다: "===== 2026-11-05 09:00:01 RUN START ====="
        # 느슨하게 찾으면 로그에 적어 둔 메모까지 실행 기록으로 오인한다.
        $hdr = '^=+\s+' + [regex]::Escape($todayStr) + '\s+\d{2}:\d{2}:\d{2}\s+RUN START'
        for ($i = 0; $i -lt $log.Count; $i++) {
            if ($log[$i] -match $hdr) { $startIdx = $i }
        }
        if ($startIdx -ge 0) {
            $hasToday = $true
            $m = [regex]::Match($log[$startIdx], '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
            if ($m.Success) { $startTime = $m.Groups[1].Value }

            for ($i = $startIdx; $i -lt $log.Count; $i++) {
                $me = [regex]::Match($log[$i], 'EXIT CODE (\d+)')
                if ($me.Success) { $exitCode = [int]$me.Groups[1].Value; break }
                if ($log[$i] -like '*"type":"result"*') {
                    try {
                        $o = $log[$i] | ConvertFrom-Json
                        if ($o.result) { $resultMsg = (($o.result -split "`n")[0]).Trim() }
                    } catch { }
                }
            }
        }
    }

    # --- 판정 ---
    if (-not $hasToday) {
        if ($task.State -eq 'Running') {
            $state = '실행 중'
            $detail = '로그에 아직 기록이 없지만 작업이 돌고 있습니다.'
        } else {
            $state = '안 돌았음'
            $detail = '오늘(' + $todayStr + ') 실행 기록이 전혀 없습니다. 예약 시각 ' + $j.Due + ' 이 지났는데도 호출되지 않았습니다.'
            $problems++
        }
    } elseif ($null -eq $exitCode) {
        if ($task.State -eq 'Running') {
            $state = '실행 중'
            $detail = $startTime + ' 에 시작해 아직 끝나지 않았습니다. (제한 1시간)'
        } else {
            $state = '중간에 죽음'
            $detail = $startTime + ' 에 시작했으나 종료 기록이 없고 작업도 멈춰 있습니다.'
            $problems++
        }
    } elseif ($exitCode -eq 0) {
        $state = '성공'
        $detail = $startTime + ' 시작, 정상 종료.'
        if ($resultMsg) { $detail += '  요약: ' + $resultMsg }
    } else {
        $state = '실패'
        $detail = $startTime + ' 시작, 종료 코드 ' + $exitCode + '.'
        if ($resultMsg) { $detail += '  사유: ' + $resultMsg }
        $problems++
    }

    $lines.Add('[' + $state + '] ' + $j.Label)
    $lines.Add('    ' + $detail)
    $lines.Add('    스케줄러: 마지막 실행 ' + $info.LastRunTime + ' / 결과 ' + $info.LastTaskResult + ' / 놓친 회차 ' + $info.NumberOfMissedRuns + ' / 다음 ' + $info.NextRunTime)
    $lines.Add('    로그: ' + $logPath)
    $lines.Add('')

    if ($state -ne '성공' -and $state -ne '실행 중') {
        $summary.Add($j.Label + ': ' + $state)
    }
}

if ($problems -gt 0) {
    $lines.Add('--- 다시 돌리는 방법 ---')
    $lines.Add('Start-ScheduledTask -TaskName "eCoDY ECM 일일 모니터링"')
    $lines.Add('또는 Claude Code 에서 "eCoDY 모니터링 실행" 이라고 말하면 됩니다.')
}

$text = [string]::Join("`r`n", $lines)

# --- 이력은 항상 남긴다 ---
$history = Join-Path $WatchDir ('check-' + $now.ToString('yyyy-MM') + '.log')
Add-Content -LiteralPath $history -Value ($text + "`r`n" + ('=' * 60) + "`r`n") -Encoding UTF8

Write-Output $text

# --- 문제가 있으면 눈에 띄게 알린다 ---
if ($problems -gt 0) {
    $alert = Join-Path $WatchDir ('ALERT-' + $todayStr + '.txt')

    # 하루에 한 번만 알린다. 보고서 파일이 이미 있으면 내용만 갱신하고 조용히 넘어간다.
    $alreadyAlerted = Test-Path -LiteralPath $alert

    Set-Content -LiteralPath $alert -Value $text -Encoding UTF8

    if ($alreadyAlerted) {
        Write-Output '(오늘 이미 알렸으므로 창을 띄우지 않습니다)'
        exit 2
    }

    $head = '예약 실행 점검: 문제 ' + $problems + '건 - ' + [string]::Join(' / ', $summary)

    # 1) 윈도 알림 (되면 좋고, 안 되면 넘어간다)
    try {
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
        $tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $nodes = $tpl.GetElementsByTagName('text')
        $nodes.Item(0).AppendChild($tpl.CreateTextNode('예약 실행 점검')) | Out-Null
        $nodes.Item(1).AppendChild($tpl.CreateTextNode($head)) | Out-Null
        $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show(
            [Windows.UI.Notifications.ToastNotification]::new($tpl))
    } catch { }

    # 2) 소리
    try { for ($b = 0; $b -lt 3; $b++) { [console]::beep(880, 180); Start-Sleep -Milliseconds 120 } } catch { }

    # 3) 보고서를 띄운다 - 이것이 확실한 통지 수단이다
    if (-not $NoPopup) {
        try { Start-Process -FilePath 'notepad.exe' -ArgumentList ('"' + $alert + '"') } catch { }
    }

    exit 2
}

exit 0
