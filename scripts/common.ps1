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
        "C:\Program Files\Python312\python.exe"
    )

    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            return $Candidate
        }
    }

    try {
        $Executable = py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $Executable) {
            return $Executable.Trim()
        }
    } catch {
    }

    throw "Python 3.12 is missing or only available as a blocked Store alias. Install Python 3.12 from python.org, then rerun this command."
}

