# Docker Compose runner for News Automation Dashboard (PowerShell)
param(
    [Parameter(Position=0)]
    [string]$Action = "up",
    [switch]$DryRun,
    [switch]$Test,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Ensure directories and files exist before mounting
if (-not (Test-Path "config.json") -and (Test-Path "config.example.json")) {
    Write-Host "Notice: config.json not found, initializing from config.example.json..." -ForegroundColor Yellow
    Copy-Item "config.example.json" -Destination "config.json"
}
if (-not (Test-Path "daily-summary.md")) {
    New-Item -ItemType File -Path "daily-summary.md" -Force | Out-Null
}
if (-not (Test-Path "digests")) {
    New-Item -ItemType Directory -Path "digests" -Force | Out-Null
}
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" -Force | Out-Null
}

$containerTool = "docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue) -and (Get-Command podman -ErrorAction SilentlyContinue)) {
    $containerTool = "podman"
}

$port = if ($env:PORT) { $env:PORT } else { "58619" }

switch ($Action.ToLower()) {
    { $_ -in "up", "start", "server" } {
        Write-Host "Starting News Automation Dashboard stack on port $port..." -ForegroundColor Cyan
        & $containerTool compose up -d
        Write-Host "Dashboard available at: http://localhost:$port" -ForegroundColor Green
    }
    "logs" {
        & $containerTool compose logs -f
    }
    { $_ -in "down", "stop" } {
        Write-Host "Stopping News Automation Dashboard stack..." -ForegroundColor Yellow
        & $containerTool compose down
    }
    "build" {
        Write-Host "Building container images..." -ForegroundColor Cyan
        & $containerTool compose build
    }
    { $_ -in "cli", "run" } {
        $runArgs = @("compose", "--profile", "cli", "run", "--rm", "news-runner")
        if ($DryRun) { $runArgs += "--dry-run" }
        if ($Test) { $runArgs += "--test" }
        if ($RemainingArgs) { $runArgs += $RemainingArgs }
        Write-Host "Executing news-runner CLI inside container..." -ForegroundColor Cyan
        & $containerTool $runArgs
    }
    default {
        Write-Host "Usage: .\run-docker.ps1 [up|down|logs|build|cli] [-DryRun] [-Test]" -ForegroundColor Cyan
        Write-Host "  up    - Launch the Operations Dashboard on port $port"
        Write-Host "  down  - Stop all running containers"
        Write-Host "  logs  - Stream live logs from all containers"
        Write-Host "  build - Rebuild container images"
        Write-Host "  cli   - Run daily_news.py CLI in container (e.g. .\run-docker.ps1 cli -DryRun)"
    }
}
