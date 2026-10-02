# ==========================================================================
#  PJ_Variant.ps1  -  read / switch the OEUK variant in PJ_Define.h
# --------------------------------------------------------------------------
#  Location : <project folder>\Build\   (same folder as Build.bat)
#  Called by: Build_Hook_<MODEL>.bat (-Action target)
#             BuildVariants.bat      (-Action plan / apply)
#             PostPackage.bat        (-Action folder)
#  Actions  :
#    target  print JENKINS_BUILD_TARGET (CURRENT | TEST | ALL), default CURRENT
#    plan    print the build list, one "<OEUK> <version|KEEP>" per line
#              base = first OEUK option that is not OEUK_TEST
#              TEST : <base> KEEP / OEUK_TEST KEEP     (versions untouched)
#              ALL  : <base> <ver> / OEUK_TEST <ver> /
#                     <base> <ver+1> / OEUK_TEST <ver+1>  (+1 with carry)
#    apply   enable -Variant (other OEUK options are commented out) and,
#            unless -Version is KEEP, write it into that block
#    folder  print "<folder OEUK> <version folder>" for -Variant
#              OEUK_HE1I -> OEUK_HE1I 26810
#              OEUK_TEST -> OEUK_HE1I 26810_test   (base version + _test)
#  Version  : SOFTWARE_VERSION_<n> digits are read from the OEUK block first,
#             digits not in the block from the common area outside all OEUK
#             blocks, joined in index order.
#               APP  0..4 in block                  -> 26810
#               FBL  0..2 in block + 3..7 common    -> HE130I02
#  Note     : file bytes and line endings are preserved (latin1 round trip).
#             BuildVariants.bat restores PJ_Define.h after the builds.
# ==========================================================================
param(
    [Parameter(Mandatory = $true)][ValidateSet('target', 'plan', 'apply', 'folder')][string]$Action,
    [Parameter(Mandatory = $true)][string]$File,
    [string]$Variant,
    [string]$Version
)
$ErrorActionPreference = 'Stop'
$TestVariant = 'OEUK_TEST'
$Enc = [Text.Encoding]::GetEncoding(28591)
$VerPat = '#define\s+SOFTWARE_VERSION_(\d+)\s+\(u8\)''(.)'''

function Get-Options([string]$t) {
    @([regex]::Matches($t, '(?m)^[ \t]*(?://[ \t]*)?#define[ \t]+(OEUK_\w+)') |
        ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique)
}

function Get-Base([string]$t) {
    Get-Options $t | Where-Object { $_ -ne $TestVariant } | Select-Object -First 1
}

function Get-Block([string]$t, [string]$name) {
    $m = [regex]::Match($t, '(?s)defined\s*\(\s*' + [regex]::Escape($name) + '\s*\)(.*?)#\s*(elif|else|endif)')
    if ($m.Success) { return $m.Groups[1] }
    return $null
}

# SOFTWARE_VERSION digits : block first, then the common area (outside every OEUK block)
function Get-VersionMap([string]$t, [string]$name) {
    $b = Get-Block $t $name
    if (-not $b) { return $null }
    $spans = @([regex]::Matches($t, '(?s)defined\s*\(\s*OEUK_\w+\s*\)(.*?)#\s*(elif|else|endif)') | ForEach-Object { $_.Groups[1] })
    $map = @{}
    foreach ($m in [regex]::Matches($t, $VerPat)) {
        $inside = $false
        foreach ($s in $spans) { if ($m.Index -ge $s.Index -and $m.Index -lt $s.Index + $s.Length) { $inside = $true; break } }
        if (-not $inside) { $map[[int]$m.Groups[1].Value] = @{ Char = $m.Groups[2].Value; InBlock = $false } }
    }
    foreach ($m in [regex]::Matches($b.Value, $VerPat)) {
        $map[[int]$m.Groups[1].Value] = @{ Char = $m.Groups[2].Value; InBlock = $true }
    }
    return $map
}

function Get-Version([string]$t, [string]$name) {
    $map = Get-VersionMap $t $name
    if (-not $map -or $map.Count -eq 0) { return $null }
    $v = ''
    foreach ($i in 0..($map.Count - 1)) {
        if (-not $map.ContainsKey($i)) { return $null }
        $v += $map[$i].Char
    }
    return $v
}

function Get-Markers([string]$t, [string]$name) {
    $b = Get-Block $t $name
    if (-not $b) { return '' }
    ([regex]::Matches($b.Value, '(FOTA_OTA_\d+|HAE_HSM_\w+)') | ForEach-Object { $_.Value } | Sort-Object -Unique) -join ','
}

function Get-NextVersion([string]$v) {
    if ($v -notmatch '^\d+$') { throw "version '$v' is not all digits - ALL (version +1) cannot be used, use TEST" }
    $n = [long]$v + 1
    $s = $n.ToString().PadLeft($v.Length, '0')
    if ($s.Length -gt $v.Length) { throw "version '$v' + 1 overflows $($v.Length) digits" }
    return $s
}

function Get-Target([string]$t) {
    $m = [regex]::Match($t, '(?m)^[ \t]*#define[ \t]+JENKINS_BUILD_TARGET[ \t]+(\w+)')
    if ($m.Success) { return $m.Groups[1].Value.ToUpper() }
    return 'CURRENT'
}

try {
    $text = [IO.File]::ReadAllText($File, $Enc)

    switch ($Action) {
        'target' {
            Write-Output (Get-Target $text)
        }
        'plan' {
            $mode = Get-Target $text
            if ($mode -ne 'TEST' -and $mode -ne 'ALL') { throw "JENKINS_BUILD_TARGET is '$mode' - plan is only for TEST or ALL" }
            $opts = Get-Options $text
            if ($opts -notcontains $TestVariant) { throw "$TestVariant option not found in PJ_Define.h" }
            $base = Get-Base $text
            if (-not $base) { throw "no base OEUK option (other than $TestVariant) in PJ_Define.h" }
            if (-not (Get-Block $text $TestVariant)) { throw "#if/#elif block for $TestVariant not found" }
            $mb = Get-Markers $text $base
            $mt = Get-Markers $text $TestVariant
            if ($mb -ne $mt) {
                throw "FOTA/HSM setting differs ($base : $mb / $TestVariant : $mt) - needs the same setting, use build_all.bat"
            }
            $ver = Get-Version $text $base
            if (-not $ver) { throw "SOFTWARE_VERSION digits not found for $base" }
            if ($mode -eq 'TEST') {
                Write-Output "$base KEEP"
                Write-Output "$TestVariant KEEP"
            }
            else {
                $map = Get-VersionMap $text $base
                $outside = @($map.Keys | Where-Object { -not $map[$_].InBlock })
                if ($outside.Count -gt 0) { throw "version digits $($outside -join ',') are outside the $base block - ALL cannot be used, use TEST" }
                $next = Get-NextVersion $ver
                Write-Output "$base $ver"
                Write-Output "$TestVariant $ver"
                Write-Output "$base $next"
                Write-Output "$TestVariant $next"
            }
        }
        'apply' {
            $opts = Get-Options $text
            if ($opts -notcontains $Variant) { throw "variant '$Variant' not found in PJ_Define.h" }

            # 1) only the target OEUK option stays enabled
            $text = [regex]::Replace($text, '(?m)^([ \t]*)(?://[ \t]*)?(#define[ \t]+)(OEUK_\w+)', {
                param($m)
                if ($m.Groups[3].Value -eq $Variant) { $m.Groups[1].Value + $m.Groups[2].Value + $m.Groups[3].Value }
                else { $m.Groups[1].Value + '// ' + $m.Groups[2].Value + $m.Groups[3].Value }
            })

            # 2) version of the target block (ALL only, KEEP leaves it)
            if ($Version -and $Version -ne 'KEEP') {
                $b = Get-Block $text $Variant
                if (-not $b) { throw "#if/#elif block for $Variant not found" }
                $body = $b.Value
                foreach ($i in 0..($Version.Length - 1)) {
                    $pat = '(#define\s+SOFTWARE_VERSION_' + $i + '\s+\(u8\)'')(.)('')'
                    if (-not [regex]::IsMatch($body, $pat)) { throw "SOFTWARE_VERSION_$i not found in $Variant block" }
                    $ch = [string]$Version[$i]
                    $body = [regex]::Replace($body, $pat, { param($m) $m.Groups[1].Value + $ch + $m.Groups[3].Value })
                }
                $text = $text.Substring(0, $b.Index) + $body + $text.Substring($b.Index + $b.Length)
            }
            [IO.File]::WriteAllText($File, $text, $Enc)

            # 3) read back
            $chk = [IO.File]::ReadAllText($File, $Enc)
            $on = @([regex]::Matches($chk, '(?m)^[ \t]*#define[ \t]+(OEUK_\w+)') | ForEach-Object { $_.Groups[1].Value })
            $got = Get-Version $chk $Variant
            if ($on.Count -ne 1 -or $on[0] -ne $Variant) { throw "read back mismatch (enabled: $($on -join ','))" }
            if ($Version -and $Version -ne 'KEEP' -and $got -ne $Version) { throw "read back mismatch (version: $got)" }
            Write-Output "[PJ_Variant] $Variant enabled, version $got"
        }
        'folder' {
            if (-not $Variant) { throw "-Variant is required" }
            $folder = $Variant
            if ($Variant -eq $TestVariant) {
                $base = Get-Base $text
                if ($base) { $folder = $base }
            }
            $ver = Get-Version $text $folder
            if (-not $ver) { $ver = 'UNKNOWN' }
            if ($Variant -eq $TestVariant -and $folder -ne $Variant -and $ver -ne 'UNKNOWN') { $ver = $ver + '_test' }
            Write-Output "$folder $ver"
        }
    }
    exit 0
}
catch {
    Write-Output "[PJ_Variant] ERROR: $($_.Exception.Message)"
    exit 2
}
