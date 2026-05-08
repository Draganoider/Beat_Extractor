param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Song,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Python = Get-BeatExtractorPython
& $Python -m beat_extractor.cli_generate $Song @Rest
exit $LASTEXITCODE

