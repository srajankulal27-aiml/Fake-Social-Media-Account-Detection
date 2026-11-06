# PowerShell Launch Script for FSMD FastAPI Application
# Run with: .\run.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Fake Social Media Detection (FSMD) Web App..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Error: Virtual environment python.exe not found at $PythonExe" -ForegroundColor Red
    Write-Host "Please ensure .venv is configured." -ForegroundColor Yellow
    exit 1
}

Write-Host "Checking core dependencies..." -ForegroundColor Green
& $PythonExe -c "import numpy, pandas, sklearn, shap, fastapi, uvicorn; print('Environment dependencies verified.')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed dependency check." -ForegroundColor Red
    exit 1
}

Write-Host "`nLaunching server on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate the application.`n" -ForegroundColor Yellow

& $PythonExe -m uvicorn app_api.main:app --host 127.0.0.1 --port 8000 --reload

