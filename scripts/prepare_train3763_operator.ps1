param([string]$Python = 'python', [string]$Directory = 'data/processed/operator-venv')
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $operatorRoot = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Directory))
    $allowedRoot = [IO.Path]::GetFullPath((Join-Path (Get-Location) 'data/processed')) + [IO.Path]::DirectorySeparatorChar
    if (-not $operatorRoot.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Operator environment must be under ignored data/processed.'
    }
    if (Test-Path -LiteralPath $operatorRoot) { throw 'Use a new directory; existing environments are retained.' }
    & $Python -m venv $operatorRoot
    if ($LASTEXITCODE -ne 0) { throw 'Isolated venv creation failed.' }
    $operatorPython = Join-Path $operatorRoot 'Scripts/python.exe'
    & $operatorPython -m pip install --disable-pip-version-check --index-url https://pypi.org/simple 'kaggle==2.2.5' 'kagglesdk==0.1.38' 'requests==2.34.2'
    if ($LASTEXITCODE -ne 0) { throw 'Pinned installation failed; keep partial environment and use a new directory after diagnosis.' }
    & $operatorPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependencies are inconsistent.' }
    & $operatorPython -B -c 'from safeshift.internvl3763_operator import check_sdk; print(check_sdk())'
    if ($LASTEXITCODE -ne 0) { throw 'SDK pin verification failed.' }
    & $operatorPython -m pip freeze | Out-File -LiteralPath (Join-Path $operatorRoot 'freeze.txt') -Encoding utf8
    # No Kaggle import/authentication/job/API call in this script.
} finally { Pop-Location }
