$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Python = Get-BeatExtractorPython

& $Python -m pytest
exit $LASTEXITCODE
