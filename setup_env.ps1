# setup_env.ps1
# PowerShell script to install dependencies on Windows via winget and initialize virtual environments.

Write-Host "=== ZR4K Environment Setup ===" -ForegroundColor Cyan

# Ensure script runs with administrator rights if services need to be started
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script might need Administrator privileges to query or start system services."
}

# 1. Install & Verify PostgreSQL
Write-Host "`n[1/4] Checking PostgreSQL service..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService) {
    $name = $pgService.Name
    $status = $pgService.Status
    Write-Host "PostgreSQL Service '$name' is $status." -ForegroundColor Green
    if ($status -ne "Running") {
        Write-Host "Starting PostgreSQL Service..." -ForegroundColor Cyan
        Start-Service -Name $name -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "PostgreSQL service not found. Installing via winget..." -ForegroundColor Cyan
    winget install PostgreSQL.PostgreSQL.16 --silent --accept-package-agreements --accept-source-agreements
    Write-Host "PostgreSQL installation initiated. Please verify installation finish in your start menu or system services." -ForegroundColor Green
}

# 2. Install & Verify Redis
Write-Host "`n[2/4] Checking Redis service..." -ForegroundColor Yellow
$redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
if ($redisService) {
    $status = $redisService.Status
    Write-Host "Redis Service is $status." -ForegroundColor Green
    if ($status -ne "Running") {
        Write-Host "Starting Redis Service..." -ForegroundColor Cyan
        Start-Service -Name "Redis" -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Redis not found. Installing via winget (Redis 3.0.504 stable)..." -ForegroundColor Cyan
    winget install Redis.Redis --silent --accept-package-agreements --accept-source-agreements
    Write-Host "Redis installation initiated. Attempting to start service..." -ForegroundColor Green
    Start-Service -Name "Redis" -ErrorAction SilentlyContinue
}

# 3. Create Python Venv & Install Requirements
Write-Host "`n[3/4] Configuring Python Virtual Environment..." -ForegroundColor Yellow
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPath = Join-Path $ScriptDir "backend\.venv"

if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating Python venv at '$VenvPath'..." -ForegroundColor Cyan
    python -m venv "$VenvPath"
} else {
    Write-Host "Python venv already exists." -ForegroundColor Green
}

Write-Host "Upgrading pip and installing requirements..." -ForegroundColor Cyan
& "$VenvPath\Scripts\python.exe" -m pip install --upgrade pip
& "$VenvPath\Scripts\pip.exe" install -r (Join-Path $ScriptDir "backend\requirements.txt")

# 4. Install Node modules
Write-Host "`n[4/4] Configuring Frontend Node Modules..." -ForegroundColor Yellow
$FrontendPath = Join-Path $ScriptDir "frontend"
if (Test-Path $FrontendPath) {
    Push-Location $FrontendPath
    Write-Host "Running npm install in '$FrontendPath'..." -ForegroundColor Cyan
    npm install
    Pop-Location
} else {
    Write-Warning "Frontend directory not found at '$FrontendPath'. Please initialize frontend first."
}

Write-Host "`n=== Setup Completed Successfully! ===" -ForegroundColor Green
Write-Host "Please edit backend/.env with your secrets before running." -ForegroundColor Yellow
