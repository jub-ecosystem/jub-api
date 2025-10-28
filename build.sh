#!/bin/bash
readonly JUB_IMAGE_NAME=${1:-"jubapi:latest"}

docker build -t ${JUB_IMAGE_NAME} -f Dockerfile .