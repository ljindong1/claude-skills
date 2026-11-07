# 주 1회 자동 동기화 (작업 스케줄러가 부른다).
#
# sync 까지만 한다 - 회사 저장소의 새 커밋을 걸러 로컬 사본 브랜치에 쌓는다.
# 푸시는 하지 않는다. 밖으로 나가는 일은 사람이 보고 승인한다 (사용자 결정 2026-11-07).
# 올릴 것이 생기면 알림 창을 띄워 알려 준다.
#
# 등록:  scripts\install_weekly_task.ps1
# 로그:  %LOCALAPPDATA%\joule-repo-sync\weekly.log
param(
    [int]$PopupSeconds = 0,     # 0 = 사용자가 닫을 때까지
    [switch]$NoPopup            # 시험용: 창을 띄우지 않는다
)

$ErrorActionPreference = 'Continue'
# 스케줄러가 부른 세션은 콘솔 인코딩이 cp949 라, 그대로 두면 python 의 한글 출력이
# 로그에서 깨진다 (대화형 터미널에서는 안 드러난다).
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$syncScript = Join-Path $here 'sync_mirror.py'
$work = 'D:\Ljindong\joule'

$logDir = Join-Path $env:LOCALAPPDATA 'joule-repo-sync'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$log = Join-Path $logDir 'weekly.log'

function Write-Log($text) { $text | Out-File -Append -Encoding utf8 $log }

Write-Log ""
Write-Log ("=== {0} ===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

$env:PYTHONIOENCODING = 'utf-8'

# preview 를 먼저 남긴다. sync 가 돌고 나면 '덧붙일 커밋 0 개' 가 되어
# '사본에 처음 들어가는 확장자·폴더' 점검을 아무도 볼 수 없기 때문이다.
# 푸시 전에 사람이 이 로그를 읽는다.
Write-Log "  --- preview ---"
$prev = & python $syncScript preview 2>&1
$prev | ForEach-Object { Write-Log ("  " + $_) }

Write-Log "  --- sync ---"
$out = & python $syncScript sync --no-fetch 2>&1
$code = $LASTEXITCODE
$out | ForEach-Object { Write-Log ("  " + $_) }
Write-Log ("  (종료 코드 {0})" -f $code)

# 올릴 것이 남았는지: 사본 브랜치가 GitHub 보다 앞서 있나
$ahead = 0
try {
    $local = (& git -C $work rev-parse public 2>$null).Trim()
    $remote = (& git -C $work rev-parse origin/main 2>$null).Trim()
    if ($local -and $remote -and ($local -ne $remote)) {
        $ahead = [int](& git -C $work rev-list --count "origin/main..public").Trim()
    }
} catch {
    Write-Log ("  [경고] 사본 상태를 읽지 못했다: " + $_.Exception.Message)
}

if ($code -ne 0) {
    $msg = "joule 동기화(주간)가 끝내지 못했습니다.`n`n" +
           "로그: $log`n`n" +
           "Claude 에게 '동기화 확인해줘' 라고 하시면 원인을 봐 드립니다."
    $title = 'joule 동기화 - 확인 필요'
} elseif ($ahead -gt 0) {
    $msg = "joule 사본에 올릴 커밋이 $ahead 개 쌓였습니다.`n`n" +
           "Claude 에게 '동기화 푸시해줘' 라고 하시거나,`n" +
           "터미널에서 sync_mirror.py push 를 돌리세요.`n`n" +
           "(쌓기는 끝났고 GitHub 로 보내는 것만 남았습니다)"
    $title = 'joule 동기화 - 올릴 것이 있습니다'
} else {
    Write-Log "  올릴 것 없음 - 알림을 띄우지 않는다."
    exit 0
}

Write-Log ("  알림: " + $title)
if (-not $NoPopup) {
    try {
        $sh = New-Object -ComObject Wscript.Shell
        $sh.Popup($msg, $PopupSeconds, $title, 64) | Out-Null
    } catch {
        Write-Log ("  [경고] 알림 창을 띄우지 못했다: " + $_.Exception.Message)
    }
}
exit 0
