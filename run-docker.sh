#!/usr/bin/env bash
# Docker Compose runner for News Automation Dashboard
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure directories and files exist before mounting
if [ ! -f config.json ] && [ -f config.example.json ]; then
  echo "Notice: config.json not found, initializing from config.example.json..."
  cp config.example.json config.json
fi

if [ ! -f daily-summary.md ]; then
  touch daily-summary.md
fi

mkdir -p digests data

# Select compose CLI (docker or podman fallback)
if command -v docker >/dev/null 2>&1; then
  CONTAINER_TOOL="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_TOOL="podman"
else
  echo "[ERROR] Neither docker nor podman was found on PATH." >&2
  exit 1
fi

COMMAND="${1:-}"

case "$COMMAND" in
  up|start|server)
    echo "Starting News Automation Dashboard stack on port ${PORT:-58619}..."
    $CONTAINER_TOOL compose up -d
    echo "Dashboard available at: http://localhost:${PORT:-58619}"
    ;;
  logs)
    $CONTAINER_TOOL compose logs -f
    ;;
  down|stop)
    echo "Stopping News Automation Dashboard stack..."
    $CONTAINER_TOOL compose down
    ;;
  build)
    echo "Building container images..."
    $CONTAINER_TOOL compose build
    ;;
  cli|run)
    shift || true
    echo "Executing news-runner CLI inside container..."
    $CONTAINER_TOOL compose --profile cli run --rm news-runner "$@"
    ;;
  *)
    echo "Usage: $0 {up|down|logs|build|cli [args...]}"
    echo "  up    - Launch the Operations Dashboard (Frontend + Backend) on port ${PORT:-58619}"
    echo "  down  - Stop all running containers"
    echo "  logs  - Stream live logs from all containers"
    echo "  build - Rebuild container images"
    echo "  cli   - Run daily_news.py CLI in container (e.g. $0 cli --dry-run)"
    ;;
esac
