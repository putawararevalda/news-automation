# Docker Compose runner for News Automation (PowerShell)
param(
    [Parameter(Position=0)]
    [string]$Action = "",
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$containerTool = "docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue) -and (Get-Command podman -ErrorAction SilentlyContinue)) {
    $containerTool = "podman"
}

switch ($Action.ToLower()) {
    "scheduler" {
        Write-Host "Starting news-automation scheduler daemon..." -ForegroundColor Cyan
        & $containerTool compose up -d news-scheduler
    }
    "logs" {
        & $containerTool compose logs -f news-scheduler
    }
    "down" {
        Write-Host "Stopping containers..." -ForegroundColor Yellow
        & $containerTool compose down
    }
    "build" {
        Write-Host "Building container images..." -ForegroundColor Cyan
        & $containerTool compose build
    }
    default {
        $runArgs = @("compose", "run", "--rm", "news-runner")
        if ($Action) { $runArgs += $Action }
        if ($RemainingArgs) { $runArgs += $RemainingArgs }
        Write-Host "Executing news-runner in container..." -ForegroundColor Cyan
        & $containerTool $runArgs
    }
}
