# PowerShell Test Runner for FSMD Project
# Run with: .\run_tests.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Running Full Pytest Test Suite for FSMD..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Error: Virtual environment python.exe not found at $PythonExe" -ForegroundColor Red
    exit 1
}

& $PythonExe -m pytest -v --tb=short
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "`nAll test cases PASSED successfully!" -ForegroundColor Green
} else {
    Write-Host "`nTest suite encountered failures. Exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode

