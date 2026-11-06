<#
.SYNOPSIS
    PikVaidya AI — Windows Native Production Runner
.DESCRIPTION
    Builds the Vite React frontend (if needed), verifies static mounts,
    initializes uploads storage, and launches the unified FastAPI production server.
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$RebuildFrontend = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=================================================================" -ForegroundColor Green
Write-Host " PikVaidya AI — Unified Production Environment Launcher" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "Project Root: $ProjectRoot"

# 1. Ensure uploads directory exists
$UploadsDir = Join-Path $ProjectRoot "uploads"
if (-not (Test-Path $UploadsDir)) {
    Write-Host "[1/4] Creating uploads directory: $UploadsDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $UploadsDir -Force | Out-Null
} else {
    Write-Host "[1/4] Uploads directory verified." -ForegroundColor Cyan
}

# 2. Verify or build Frontend SPA
$FrontendDist = Join-Path $ProjectRoot "frontend\dist"
$IndexHtml = Join-Path $FrontendDist "index.html"

if ($RebuildFrontend -or (-not (Test-Path $IndexHtml))) {
    Write-Host "[2/4] Compiling React 18 production bundle..." -ForegroundColor Cyan
    $FrontendDir = Join-Path $ProjectRoot "frontend"
    Push-Location $FrontendDir
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
            npm install
        }
        npm run build
        Write-Host "Frontend build completed successfully." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[2/4] Production frontend bundle found in frontend/dist." -ForegroundColor Cyan
}

# 3. Environment & Python path setup
Write-Host "[3/4] Configuring Python environment variables..." -ForegroundColor Cyan
$env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\backend"
$env:ENVIRONMENT = "production"

# 4. Launch unified FastAPI server
Write-Host "[4/4] Starting Uvicorn production server on http://$($HostAddress):$Port ..." -ForegroundColor Green
Write-Host "  - Web Dashboard:     http://localhost:$Port/"
Write-Host "  - API Documentation: http://localhost:$Port/docs"
Write-Host "  - Health Telemetry:  http://localhost:$Port/health"
Write-Host "Press Ctrl+C to terminate." -ForegroundColor Yellow

python -m uvicorn app.main:app --host $HostAddress --port $Port --app-dir "$ProjectRoot\backend"

