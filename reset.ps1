$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command py -ErrorAction Stop).Source
    & $Python -3 -m harness.reset @args
} else {
    & $Python -m harness.reset @args
}
exit $LASTEXITCODE
