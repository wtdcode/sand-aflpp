#!/bin/bash

set -ex

MYTMPDIR="$(mktemp -d)"
trap 'rm -rf -- "$MYTMPDIR"' EXIT

docker run --rm -it -v ${MYTMPDIR}:/out $1 cp -r /unibench/bin /out/bin
docker build -t $2 .
docker run -it -v ${MYTMPDIR}:/out $2 bash -c "rm -rf /unibench/bin && mkdir -p /unibench && cp -r /out/bin /unibench"

LAST="$(docker ps -lq)"
docker commit $LAST "$2-from-$1"