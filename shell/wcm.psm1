# wcm.psm1 - the `wcm` command for PowerShell (Windows PowerShell 5.1 and later).
#
# A child process cannot change its parent shell's directory, yet `wcm resume`
# promises to land you where the work is. This function wraps the CLI: it names
# a temporary file in WCM_CD_FILE, runs the CLI attached to the console (so the
# pause prompts work), and moves to the directory the CLI wrote there, if any.
#
# Install: add this line to your $PROFILE
#   Import-Module <repo>\shell\wcm.psm1

$script:WcmExe = $null
$script:PyHasWcm = $false
$script:InstallHint = 'wcm: error: the wcm CLI is not installed. Install it with: py -3.14 -m pip install <path to the working-memory-manager repository>'

function Resolve-WcmCli {
    # Positive results are cached; a missing CLI is looked up again on every
    # call, so installing it works without re-importing the module.
    if ($script:WcmExe -and (Test-Path -LiteralPath $script:WcmExe)) { return $true }
    $script:WcmExe = Get-Command wcm -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty Source
    if ($script:WcmExe) { return $true }
    if ($script:PyHasWcm) { return $true }
    # Never a bare `python`: on Windows it may be the Microsoft Store alias.
    if (Get-Command py -CommandType Application -ErrorAction SilentlyContinue) {
        & py -3.14 -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('wcm') else 1)" 2>$null
        $script:PyHasWcm = ($LASTEXITCODE -eq 0)
    }
    return $script:PyHasWcm
}

function ConvertTo-WcmArgument([object] $Value, [bool] $Legacy) {
    # PowerShell parses `--tags a,b` as an array; the CLI expects the text.
    if ($Value -is [array]) { $Value = ($Value | ForEach-Object { [string]$_ }) -join ',' }
    $s = [string]$Value
    # Windows PowerShell 5.1 drops empty arguments and passes embedded double
    # quotes unescaped. Quote those arguments ourselves, Windows-style.
    if ($Legacy -and ($s -eq '' -or $s -match '[\s"]')) {
        $s = '"' + (($s -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
    }
    return $s
}

function wcm {
    if (-not (Resolve-WcmCli)) {
        Write-Host $script:InstallHint -ForegroundColor Red
        $global:LASTEXITCODE = 1
        return
    }

    $legacy = -not (Test-Path Variable:PSNativeCommandArgumentPassing) -or
        ($PSNativeCommandArgumentPassing -eq 'Legacy')
    $argv = @(foreach ($a in $args) { ConvertTo-WcmArgument $a $legacy })

    $tmp = [System.IO.Path]::GetTempFileName()
    $previous = $env:WCM_CD_FILE
    $env:WCM_CD_FILE = $tmp
    $code = 1
    try {
        try {
            if ($script:WcmExe) {
                & $script:WcmExe @argv
            } else {
                & py -3.14 -m wcm @argv
            }
            $code = $LASTEXITCODE
        } catch [System.Management.Automation.CommandNotFoundException] {
            $script:WcmExe = $null
            Write-Host $script:InstallHint -ForegroundColor Red
            $code = 1
        }
        # -Encoding UTF8: Windows PowerShell 5.1 reads a file without BOM as ANSI.
        $target = Get-Content -LiteralPath $tmp -Encoding UTF8 -TotalCount 1 -ErrorAction SilentlyContinue
        if ($code -eq 0 -and $target -and (Test-Path -LiteralPath $target -PathType Container)) {
            Set-Location -LiteralPath $target
        }
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        if ($null -eq $previous) {
            Remove-Item Env:WCM_CD_FILE -ErrorAction SilentlyContinue
        } else {
            $env:WCM_CD_FILE = $previous
        }
    }
    $global:LASTEXITCODE = $code
}

Export-ModuleMember -Function wcm
