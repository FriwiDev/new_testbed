#!/bin/bash
set -e

if [ ! $# -gt 0 ]
then
  echo "./generate_topology.sh <script.py> <args>"
  exit 1
fi

[ -d "$( dirname "$0" )/work" ] || mkdir "$( dirname "$0" )/work"
python3 "$@" > "$( dirname "$0" )/work/current_topology.json"

echo "Generation script executed"
