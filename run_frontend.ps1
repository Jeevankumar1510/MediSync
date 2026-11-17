Write-Host "Starting MediSync AI Frontend Dashboard..." -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host "Launching Next.js App Router on http://localhost:3000..." -ForegroundColor Green
npm run dev
