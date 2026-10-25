$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$py = if ($env:LAB_PYTHON) { $env:LAB_PYTHON } else { 'python' }
& $py -m lab.cli @args
exit $LASTEXITCODE
