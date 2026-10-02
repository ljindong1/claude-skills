# ==========================================================================
#  PJ_Variant.ps1  -  read / switch the OEUK variant in PJ_Define.h
# --------------------------------------------------------------------------
#  Location : <project folder>\Build\   (same folder as Build.bat)
#  Called by: Build_Hook_<MODEL>.bat (-Action target)
#             BuildVariants.bat      (-Action plan / apply)
#  Actions  :
#    target  print JENKINS_BUILD_TARGET (CURRENT | ALL). no define -> CURRENT
#    plan    print the ALL build list, one "<OEUK> <version>" per line
#              base       = first OEUK option that is not OEUK_TEST
#              version    = SOFTWARE_VERSION_0..4 of the base block
#              next       = version + 1 (carry, e.g. 26819 -> 26820)
#              lines      : <base> <ver> / OEUK_TEST <ver> /
#                           <base> <next> / OEUK_TEST <next>
#    apply   enable -Variant (other OEUK options are commented out) and
#            write -Version into SOFTWARE_VERSION_0..4 of that block
#  Note     : file bytes and line endings are preserved (latin1 round trip).
#             BuildVariants.bat restores PJ_Define.h after the builds.
# ==========================================================================
param(
    [Parameter(Mandatory = $true)][ValidateSet('target', 'plan', 'apply')][string]$Action,
    [Parameter(Mandatory = $true)][string]$File,
    [string]$Variant,
    [string]$Version
)
$ErrorActionPreference = 'Stop'
$TestVariant = 'OEUK_TEST'
$Enc = [Text.Encoding]::GetEncoding(28591)

function Get-Options([string]$t) {
    [regex]::Matches($t, '(?m)^[ \t]*(?://[ \t]*)?#define[ \t]+(OEUK_\w+)') |
        ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
}

function Get-Block([string]$t, [string]$name) {
    $m = [regex]::Match($t, '(?s)defined\s*\(\s*' + [regex]::Escape($name) + '\s*\)(.*?)#\s*(elif|else|endif)')
    if ($m.Success) { return $m.Groups[1] }
    return $null
}

function Get-Version([string]$t, [string]$name) {
    $b = Get-Block $t $name
    if (-not $b) { return $null }
    $v = ''
    foreach ($i in 0..4) {
        $m = [regex]::Match($b.Value, '#define\s+SOFTWARE_VERSION_' + $i + '\s+\(u8\)''(.)''')
        if (-not $m.Success) { return $null }
        $v += $m.Groups[1].Value
    }
    return $v
}

function Get-Markers([string]$t, [string]$name) {
    $b = Get-Block $t $name
    if (-not $b) { return '' }
    ([regex]::Matches($b.Value, '(FOTA_OTA_\d+|HAE_HSM_\w+)') | ForEach-Object { $_.Value } | Sort-Object -Unique) -join ','
}

function Get-NextVersion([string]$v) {
    if ($v -notmatch '^\d{5}$') { throw "version '$v' is not 5 digits - cannot add 1" }
    $n = [int]$v + 1
    if ($n -gt 99999) { throw "version '$v' + 1 overflows 5 digits" }
    return $n.ToString('00000')
}

try {
    $text = [IO.File]::ReadAllText($File, $Enc)

    switch ($Action) {
        'target' {
            $m = [regex]::Match($text, '(?m)^[ \t]*#define[ \t]+JENKINS_BUILD_TARGET[ \t]+(\w+)')
            if ($m.Success) { Write-Output $m.Groups[1].Value.ToUpper() } else { Write-Output 'CURRENT' }
        }
        'plan' {
            $opts = @(Get-Options $text)
            if ($opts -notcontains $TestVariant) { throw "$TestVariant option not found in PJ_Define.h" }
            $base = $opts | Where-Object { $_ -ne $TestVariant } | Select-Object -First 1
            if (-not $base) { throw "no base OEUK option (other than $TestVariant) in PJ_Define.h" }
            if (-not (Get-Block $text $TestVariant)) { throw "#if/#elif block for $TestVariant not found" }
            $mb = Get-Markers $text $base
            $mt = Get-Markers $text $TestVariant
            if ($mb -ne $mt) {
                throw "FOTA/HSM setting differs ($base : $mb / $TestVariant : $mt) - ALL mode needs the same setting, use Build_all.bat"
            }
            $ver = Get-Version $text $base
            if (-not $ver) { throw "SOFTWARE_VERSION_0..4 not found in $base block" }
            $next = Get-NextVersion $ver
            Write-Output "$base $ver"
            Write-Output "$TestVariant $ver"
            Write-Output "$base $next"
            Write-Output "$TestVariant $next"
        }
        'apply' {
            $opts = @(Get-Options $text)
            if ($opts -notcontains $Variant) { throw "variant '$Variant' not found in PJ_Define.h" }
            if ($Version -notmatch '^\d{5}$') { throw "version '$Version' is not 5 digits" }

            # 1) only the target OEUK option stays enabled
            $text = [regex]::Replace($text, '(?m)^([ \t]*)(?://[ \t]*)?(#define[ \t]+)(OEUK_\w+)', {
                param($m)
                if ($m.Groups[3].Value -eq $Variant) { $m.Groups[1].Value + $m.Groups[2].Value + $m.Groups[3].Value }
                else { $m.Groups[1].Value + '// ' + $m.Groups[2].Value + $m.Groups[3].Value }
            })

            # 2) version of the target block
            $b = Get-Block $text $Variant
            if (-not $b) { throw "#if/#elif block for $Variant not found" }
            $body = $b.Value
            foreach ($i in 0..4) {
                $pat = '(#define\s+SOFTWARE_VERSION_' + $i + '\s+\(u8\)'')(.)('')'
                if (-not [regex]::IsMatch($body, $pat)) { throw "SOFTWARE_VERSION_$i not found in $Variant block" }
                $ch = [string]$Version[$i]
                $body = [regex]::Replace($body, $pat, { param($m) $m.Groups[1].Value + $ch + $m.Groups[3].Value })
            }
            $text = $text.Substring(0, $b.Index) + $body + $text.Substring($b.Index + $b.Length)
            [IO.File]::WriteAllText($File, $text, $Enc)

            # 3) read back
            $chk = [IO.File]::ReadAllText($File, $Enc)
            $on = @([regex]::Matches($chk, '(?m)^[ \t]*#define[ \t]+(OEUK_\w+)') | ForEach-Object { $_.Groups[1].Value })
            $got = Get-Version $chk $Variant
            if ($on.Count -ne 1 -or $on[0] -ne $Variant -or $got -ne $Version) {
                throw "read back mismatch (enabled: $($on -join ',') / version: $got)"
            }
            Write-Output "[PJ_Variant] $Variant enabled, version $Version"
        }
    }
    exit 0
}
catch {
    Write-Output "[PJ_Variant] ERROR: $($_.Exception.Message)"
    exit 2
}
