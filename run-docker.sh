#!/usr/bin/env bash
# Docker Compose runner for News Automation
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMMAND="${1:-}"

case "$COMMAND" in
  scheduler)
    echo "Starting news-automation scheduler daemon..."
    docker compose up -d news-scheduler
    ;;
  logs)
    docker compose logs -f news-scheduler
    ;;
  down)
    echo "Stopping containers..."
    docker compose down
    ;;
  build)
    echo "Building docker images..."
    docker compose build
    ;;
  *)
    echo "Executing news-runner in Docker..."
    docker compose run --rm news-runner "$@"
    ;;
esac
