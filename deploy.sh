#!/bin/bash
# Usage: ./deploy.sh [env_file] [build] [ui]
#   env_file  environment file (default: .env.dev)
#   build     1 = rebuild images, 0 = use existing images (default: 1)
#   ui        1 = also deploy the UI (profile "ui"), 0 = backend services only (default: 0)
readonly env_file=${1:-".env.dev"}
readonly build=${2:-1}
readonly ui=${3:-0}
# docker volume create xolo-db > /dev/null 2>&1 || true
docker network create jub > /dev/null 2>&1 || true

compose=(docker compose -p jub --env-file "$env_file" -f docker-compose.yml)
if [ "$ui" -eq 1 ]; then
    compose+=(--profile ui)
fi

echo "Using environment file: $env_file"
if [ "$ui" -eq 1 ]; then
    echo "Deploying services + UI"
    "${compose[@]}" down
else
    # Plain `down` also removes containers from inactive profiles,
    # so only stop the backend services to leave a running UI untouched.
    echo "Deploying services only (pass 1 as the 3rd argument to include the UI)"
    mapfile -t services < <("${compose[@]}" config --services)
    "${compose[@]}" down "${services[@]}"
fi

if [ "$build" -eq 1 ]; then
    echo "Building and starting containers..."
    "${compose[@]}" up -d --build
else
    echo "Starting containers without building..."
    "${compose[@]}" up -d
fi

# docker compose -p jub --env-file "$env_file" -f xolo.yml down
# docker compose -p jub --env-file "$env_file" -f xolo.yml up -d
