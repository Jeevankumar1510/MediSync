# MediSync AI - Test Runner Script
Write-Host "Running MediSync AI Backend Tests..." -ForegroundColor Cyan
& "$PSScriptRoot\backend\venv\Scripts\python.exe" -m pytest "$PSScriptRoot\backend\tests"
