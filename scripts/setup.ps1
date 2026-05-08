$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    $BasePython = Get-BeatExtractorPython -RequireBase
    & $BasePython -m venv (Join-Path $Root ".venv")
}

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
& $VenvPython -m pip install -e "$Root[dev]"
exit $LASTEXITCODE
