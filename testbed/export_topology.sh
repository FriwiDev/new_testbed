#!/bin/bash
set -e

# Usage: ./export_topology.sh [export_path]
# export_path: Defaults to "export"

if [ $# -eq 0 ]
then
  EXPORT_PATH="export"
else
  EXPORT_PATH=$1
fi

if [ ! -f "$( dirname "$0" )/work/current_topology.json" ]
then
  echo "Topology not generated yet! Please generate using generate_topology.sh!"
  exit 1
fi

python3 "$( dirname "$0" )/../src/export_topology.py" "$( dirname "$0" )/work/current_topology.json" "$EXPORT_PATH"

echo "Topology exported to \"$EXPORT_PATH\""
