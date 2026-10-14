param([switch]$CheckStartup)
$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'The .runtime Python environment is missing.' }
$projectScript = Join-Path $PSScriptRoot 'scripts\run_local.py'
if ($CheckStartup) { & $projectPython $projectScript --check-startup } else { & $projectPython $projectScript }
exit $LASTEXITCODE
