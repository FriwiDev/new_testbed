#!/bin/bash
set -e

if [ ! $# -gt 0 ]
then
  echo "./remote_topology.sh <start_all|stop_all|destroy_all>"
  echo "./remote_topology.sh <start|stop|destroy> <nodes|services>"
  echo "./remote_topology.sh ping <service1> <service2[:intf]>"
  echo "./remote_topology.sh iperf <service1> <service2[:intf]> [port] [interval] [time] [<client options> [| <server options>]]"
  echo "./remote_topology.sh ifstat <service|node> <intf>"
  echo "./remote_topology.sh <up|down> <service|node> <intf>"
  echo "./remote_topology.sh setqdisc <service|node> <intf> [<delay(ms)> [<delay-variation(ms)> [<delay-correlation(0;1)> [<loss(0;1)> [<loss-correlation(0;1)>]]]]]"
  echo "Nodes and services can be prefixed with \"node:\" or \"service:\" to resolve ambiguity."
  exit 1
fi

if [ ! -f "$( dirname "$0" )/work/current_topology.json" ]
then
  echo "Topology not generated yet! Please generate using generate_topology.sh!"
  exit 1
fi

../venv/bin/python "$( dirname "$0" )/../src/remote_topology.py" "$( dirname "$0" )/work/current_topology.json" "$@"

