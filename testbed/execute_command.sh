#!/bin/bash
set -e

if [ ! $# -gt 1 ]
then
  echo "./execute_command.sh <service_name> <cmd> [args]"
  exit 1
fi

if [ ! -f "$( dirname "$0" )/work/current_topology.json" ]
then
  echo "Topology not generated yet! Please generate using generate_topology.sh!"
  exit 1
fi

../venv/bin/python "$( dirname "$0" )/../src/execute_command.py" "$( dirname "$0" )/work/current_topology.json" "$@"
