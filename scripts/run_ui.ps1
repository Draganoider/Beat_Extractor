$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Root = Split-Path -Parent $PSScriptRoot
$App = Join-Path $Root "app.py"
$Python = Get-BeatExtractorPython

& $Python -m streamlit run $App
exit $LASTEXITCODE
