# Docker Compose runner for News Automation (PowerShell)
param(
    [Parameter(Position=0)]
    [string]$Action = "",
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

switch ($Action.ToLower()) {
    "scheduler" {
        Write-Host "Starting news-automation scheduler daemon..." -ForegroundColor Cyan
        docker compose up -d news-scheduler
    }
    "logs" {
        docker compose logs -f news-scheduler
    }
    "down" {
        Write-Host "Stopping containers..." -ForegroundColor Yellow
        docker compose down
    }
    "build" {
        Write-Host "Building docker images..." -ForegroundColor Cyan
        docker compose build
    }
    default {
        $runArgs = @("compose", "run", "--rm", "news-runner")
        if ($Action) { $runArgs += $Action }
        if ($RemainingArgs) { $runArgs += $RemainingArgs }
        Write-Host "Executing news-runner in Docker..." -ForegroundColor Cyan
        & docker $runArgs
    }
}
