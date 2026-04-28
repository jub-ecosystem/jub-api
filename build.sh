#!/bin/bash
readonly JUB_IMAGE_NAME=${1:-"jubapi:latest"}
readonly PUSH_IMAGE=${2:-"0"}
readonly CACHE=${3:-"0"}

if [[ ${CACHE} -eq 0 ]]; then
    docker build --no-cache -t ${JUB_IMAGE_NAME} -f Dockerfile .
else
    docker build -t ${JUB_IMAGE_NAME} -f Dockerfile .
fi

if [[ ${PUSH_IMAGE} -eq 1 ]]; then
    docker push ${JUB_IMAGE_NAME}
    exit 0
fi