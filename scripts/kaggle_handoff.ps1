param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('handoff','resume','report')][string]$Action,
    [Parameter(Mandatory=$true)][string]$Directory,
    [switch]$Recover,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $handoffArgs = @('-B', '-m', 'scripts.kaggle_handoff', $Action, '--directory', $Directory)
    if ($Recover) { $handoffArgs += '--recover' }
    & $Python @handoffArgs
    $handoffExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $handoffExit
