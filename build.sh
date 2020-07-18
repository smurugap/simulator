#! /bin/bash
echo "Building simulator container with tag $1"
docker build -f docker/Dockerfile . -t $1
