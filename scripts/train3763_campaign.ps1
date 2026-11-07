param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('identity','init','plan','status','abort-pre-submit','measure','forecast')][string]$Action,
    [string]$Directory = '',
    [string]$Python = 'python',
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$CampaignArguments
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $campaignArgs = @('-B', '-m', 'scripts.train3763_campaign', $Action)
    if ($Directory) { $campaignArgs += @('--directory', $Directory) }
    if ($CampaignArguments) { $campaignArgs += $CampaignArguments }
    & $Python @campaignArgs
    $campaignExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $campaignExit
