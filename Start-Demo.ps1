param([string]$MySQLServer = '', [switch]$CheckStartup)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$demoPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) {
    throw 'First run: python -m venv .venv; then .venv\Scripts\python.exe -m pip install -r requirements.txt'
}
if ($MySQLServer) { $env:MYSQLD_PATH = $MySQLServer }
if ($CheckStartup) {
    & $demoPython (Join-Path $projectRoot 'scripts\demo_server.py') --check-startup
} else {
    & $demoPython (Join-Path $projectRoot 'scripts\demo_server.py')
}
exit $LASTEXITCODE
