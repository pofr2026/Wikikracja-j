# Build and run wikikracja locally with docker-compose (includes Redis)
# Usage: 
#   Start:   .\scripts\build_docker_localy_on_windows.ps1 [-Detached] [-ResetDb]
#   Stop:    .\scripts\build_docker_localy_on_windows.ps1 -Stop
#   Restart: .\scripts\build_docker_localy_on_windows.ps1 -Restart
#   Reset DB: .\scripts\build_docker_localy_on_windows.ps1 -ResetDb

# Install Python 3.14 from python.org
# Add it to PATH
# Install venv like this:
#   py -3.14 -m venv .venv

param(
    [switch]$Detached,
    [switch]$Stop,
    [switch]$Restart,
    [switch]$ResetDb
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
$legacyDbFile = Join-Path $repoRoot "db\db.sqlite3"
$dataDbPath = Join-Path $repoRoot "data\db"

# Handle stop command
if ($Stop) {
    Write-Host "Stopping wikikracja containers..." -ForegroundColor Cyan
    docker-compose down
    
    if ($?) {
        Write-Host "`nContainers stopped and removed successfully!" -ForegroundColor Green
    } else {
        Write-Host "`nError stopping containers!" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# Handle restart command
if ($Restart) {
    Write-Host "Restarting wikikracja containers (rebuild + restart)..." -ForegroundColor Cyan
    Write-Host "Step 1/2: Stopping containers..." -ForegroundColor Yellow
    docker-compose down
    
    if (-not $?) {
        Write-Host "`nError stopping containers!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`nStep 2/2: Building and starting..." -ForegroundColor Yellow
}

# Check if Docker is running
$dockerRunning = docker info 2>$null
if (-not $?) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Stop existing containers if running
Write-Host "Stopping existing containers (if any)..." -ForegroundColor Cyan
docker-compose down 2>$null

if ($ResetDb) {
    Write-Host "`nResetting local SQLite database..." -ForegroundColor Yellow

    if (Test-Path $legacyDbFile) {
        Remove-Item $legacyDbFile -Force
        Write-Host "Deleted legacy database file: $legacyDbFile" -ForegroundColor Green
    }

    if (Test-Path $dataDbPath) {
        Remove-Item $dataDbPath -Recurse -Force
        Write-Host "Removed data volume directory: $dataDbPath" -ForegroundColor Green
    }

    New-Item -ItemType Directory -Path $dataDbPath -Force | Out-Null
    Write-Host "Recreated empty database directory: $dataDbPath" -ForegroundColor Green
}

# Build and start services with docker-compose (web + Redis)
Write-Host "`nBuilding and starting services (web + Redis)..." -ForegroundColor Green
Write-Host "Application will be available at: http://localhost:8000" -ForegroundColor Cyan

Write-Host "`nRunning docker-compose build --no-cache..." -ForegroundColor Yellow
docker-compose build --no-cache
if (-not $?) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

if ($Detached) {
    Write-Host "`nRunning in detached mode (background)" -ForegroundColor Yellow
    Write-Host "To stop: .\scripts\build_docker_localy_on_windows.ps1 -Stop`n" -ForegroundColor Yellow
    docker-compose up --build -d
    
    if ($?) {
        Write-Host "`nContainers started successfully!" -ForegroundColor Green
        Write-Host "`nUseful commands:" -ForegroundColor Cyan
        Write-Host "  - View logs:  docker-compose logs -f" -ForegroundColor White
        Write-Host "  - Stop all:   .\scripts\build_docker_localy_on_windows.ps1 -Stop" -ForegroundColor White
    }
} else {
    Write-Host "`nRunning in detached mode (background)" -ForegroundColor Yellow
    Write-Host "To stop: .\scripts\build_docker_localy_on_windows.ps1 -Stop`n" -ForegroundColor Yellow
    docker-compose up --build -d
    
    if ($?) {
        Write-Host "`nContainers started successfully!" -ForegroundColor Green
        Write-Host "`nUseful commands:" -ForegroundColor Cyan
        Write-Host "  - View logs:  docker-compose logs -f" -ForegroundColor White
        Write-Host "  - Stop all:   .\scripts\build_docker_localy_on_windows.ps1 -Stop" -ForegroundColor White
    }
}
