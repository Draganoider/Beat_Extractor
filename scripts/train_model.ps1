$Rest = $args
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Python = Get-BeatExtractorPython
& $Python -m beat_extractor.cli_train @Rest
exit $LASTEXITCODE
