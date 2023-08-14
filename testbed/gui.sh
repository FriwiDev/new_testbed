#!/bin/bash
set -e

if [ $# -gt 0 ] && [ ! "$1" == "-f" ] && [ ! "$1" == "--fullscreen" ]
then
  echo "./gui.sh [-f|--fullscreen]"
  exit 1
fi

if [ ! -f "$( dirname "$0" )/work/current_topology.json" ]
then
  echo "Topology not generated yet! Please generate using generate_topology.sh!"
  exit 1
fi

../venv/bin/python "$( dirname "$0" )/../src/gui.py" "$( dirname "$0" )/work/current_topology.json" "$@"

