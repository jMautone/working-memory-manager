# wcm.psm1 - the `wcm` command for PowerShell (Windows PowerShell 5.1 and later).
#
# A child process cannot change its parent shell's directory, yet `wcm resume`
# promises to land you where the work is. This function wraps the CLI: it names
# a temporary file in WCM_CD_FILE, runs the CLI attached to the console (so the
# pause prompts work), and moves to the directory the CLI wrote there, if any.
#
# Install: add this line to your $PROFILE
#   Import-Module <repo>\shell\wcm.psm1

# Resolved once, at import. The function below shadows the application of the
# same name, which is the point.
$script:WcmExe = Get-Command wcm -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty Source
$script:PyExe = Get-Command py -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty Source
$script:PyHasWcm = $null

function Test-WcmPackage {
    # Never a bare `python`: on Windows it may be the Microsoft Store alias.
    if ($null -eq $script:PyHasWcm) {
        & $script:PyExe -3.14 -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('wcm') else 1)" 2>$null
        $script:PyHasWcm = ($LASTEXITCODE -eq 0)
    }
    return $script:PyHasWcm
}

function wcm {
    if (-not $script:WcmExe -and -not ($script:PyExe -and (Test-WcmPackage))) {
        Write-Host "wcm: error: the wcm CLI is not installed. Install it with: py -3.14 -m pip install <path to the working-memory-manager repository>" -ForegroundColor Red
        $global:LASTEXITCODE = 1
        return
    }

    $tmp = [System.IO.Path]::GetTempFileName()
    $previous = $env:WCM_CD_FILE
    $env:WCM_CD_FILE = $tmp
    $code = 1
    try {
        if ($script:WcmExe) {
            & $script:WcmExe @args
        } else {
            & $script:PyExe -3.14 -m wcm @args
        }
        $code = $LASTEXITCODE
        # -Encoding UTF8: Windows PowerShell 5.1 reads a file without BOM as ANSI.
        $target = Get-Content -LiteralPath $tmp -Encoding UTF8 -TotalCount 1 -ErrorAction SilentlyContinue
        if ($target -and (Test-Path -LiteralPath $target -PathType Container)) {
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
