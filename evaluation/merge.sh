#!/bin/bash

set -ex

MYTMPDIR="$(mktemp -d)"
trap 'rm -rf -- "$MYTMPDIR"' EXIT

docker run --rm -it -v ${MYTMPDIR}:/out $1 cp -r /unibench/bin /out/debloat
docker run -it -v ${MYTMPDIR}:/out $2 cp -r /out/debloat /unibench/bin/

LAST="$(docker ps -lq)"
docker commit $LAST "$1-$2-merged"