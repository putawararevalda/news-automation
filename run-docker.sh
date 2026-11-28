#!/usr/bin/env bash
# Docker Compose runner for News Automation
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure config and output files exist before mounting to prevent Docker from creating them as directories
if [ ! -f config.json ] && [ -f config.example.json ]; then
  echo "Notice: config.json not found, initializing from config.example.json..."
  cp config.example.json config.json
fi

if [ ! -f daily-summary.md ]; then
  touch daily-summary.md
fi

mkdir -p digests

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
  scheduler)
    echo "Starting news-automation scheduler daemon..."
    $CONTAINER_TOOL compose up -d news-scheduler
    ;;
  logs)
    $CONTAINER_TOOL compose logs -f news-scheduler
    ;;
  down)
    echo "Stopping containers..."
    $CONTAINER_TOOL compose down
    ;;
  build)
    echo "Building container images..."
    $CONTAINER_TOOL compose build
    ;;
  *)
    echo "Executing news-runner in container..."
    $CONTAINER_TOOL compose run --rm news-runner "$@"
    ;;
esac
