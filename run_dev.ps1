# MediSync AI - Start FastAPI Dev Server
Write-Host "Starting MediSync AI Backend Server at http://localhost:8000..." -ForegroundColor Green
Write-Host "Interactive OpenAPI Docs available at http://localhost:8000/docs" -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\backend"
& "$PSScriptRoot\backend\venv\Scripts\uvicorn.exe" app.main:app --reload --port 8000
