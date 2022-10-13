#!/bin/bash
set -e

if [ ! -f "$( dirname "$0" )/work/current_topology.json" ]
then
  echo "Topology not generated yet! Please generate using generate_topology.sh!"
  exit 1
fi

python3 "$( dirname "$0" )/../src/gui.py" "$( dirname "$0" )/work/current_topology.json" "$@"

