#!/bin/bash
set -e

# Usage: ./remote_topology.sh <action> [nodes]
# action: start_all, stop_all, start, stop

if [ ! $# -gt 0 ]
then
  echo "./remote_topology.sh start_all [nodes]"
  echo "./remote_topology.sh stop_all [nodes]"
  echo "./remote_topology.sh start [services]"
  echo "./remote_topology.sh stop [services]"
  echo "Nodes or services are either a list of arguments or missing to target all nodes or services."
  echo "Start and stop can only be used after start_all has been used at least once."
  exit 1
fi

if [ ! -f "$( dirname "$0" )/work/current_topology.json" ]
then
  echo "Topology not generated yet! Please generate using generate_topology.sh!"
  exit 1
fi

python3 "$( dirname "$0" )/../src/remote_topology.py" "$( dirname "$0" )/work/current_topology.json" "$@"

