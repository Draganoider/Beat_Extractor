param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Song,
    [Alias("out")]
    [string]$OutputPath,
    [Alias("density")]
    [int]$Density,
    [Alias("min-spacing")]
    [double]$MinSpacing
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
$Root = Split-Path -Parent $PSScriptRoot
$Python = Get-BeatExtractorPython

$CliArgs = @($Song)
if ($OutputPath) {
    $CliArgs += @("--out", $OutputPath)
}
if ($Density) {
    $CliArgs += @("--density", $Density)
}
if ($MinSpacing) {
    $CliArgs += @("--min-spacing", $MinSpacing)
}

& $Python -m beat_extractor.cli @CliArgs
exit $LASTEXITCODE
