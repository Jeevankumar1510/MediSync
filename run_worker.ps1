# MediSync AI - Start Celery Background Worker
Write-Host "Starting MediSync AI Celery Background Worker..." -ForegroundColor Green
Write-Host "Connected to Redis at redis://localhost:6379/1" -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\backend"
& "$PSScriptRoot\backend\venv\Scripts\celery.exe" -A app.core.celery_app.celery_app worker --loglevel=info -P solo
