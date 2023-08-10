#!/bin/bash
set -e

if [ ! $# -gt 0 ]
then
  echo "./generate_topology.sh <script.py> <args>"
  exit 1
fi

DIRNAME=$(pwd)/$(dirname "$0")/work

[ -d "$DIRNAME" ] || mkdir "$DIRNAME"
cd "$( dirname "$1" )/../../src"
../venv/bin/python "$DIRNAME/../$1" "$DIRNAME" "${@:2}"
