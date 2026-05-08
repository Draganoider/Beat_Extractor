function Get-BeatExtractorPython {
    param(
        [switch]$RequireBase
    )

    $Root = Split-Path -Parent $PSScriptRoot
    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not $RequireBase -and (Test-Path $VenvPython)) {
        return $VenvPython
    }

    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        "C:\Python312\python.exe",
        "C:\Program Files\Python312\python.exe",
        (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\python3.12.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\python.exe")
    )

    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            try {
                & $Candidate --version *> $null
                if ($LASTEXITCODE -eq 0) {
                    return $Candidate
                }
            } catch {
            }
        }
    }

    try {
        $Executable = py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $Executable) {
            return $Executable.Trim()
        }
    } catch {
    }

    try {
        python --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return "python"
        }
    } catch {
    }

    throw "Python 3.12 is missing or blocked. Install Python 3.12 from the Microsoft Store or python.org, then rerun this command."
}
