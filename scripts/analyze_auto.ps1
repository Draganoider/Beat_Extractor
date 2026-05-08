param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Song,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Python = Get-BeatExtractorPython
& $Python -m auto_determining.cli $Song @Rest
exit $LASTEXITCODE

