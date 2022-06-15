# Testbed Concept

Sketch:

```
TOPO <-> JSON
  |
  V
Configuration builder (one for each node)
  |
  V
Configuration (files, instructions & commands)
 |          |
 V          V
File       Shell
Config     Config
Exporter   Exporter
```

Goals:

- Implement topology structure close to original distrinet to enable quick reuse of already implemented types
- Topology structures can be saved and loaded from json as a reference for future script executions
- Remove requirement of central host which manages the network (in comparison to distrinet)
- Support different node (= real hardware device) types, like servers or switches to be integrated
- Support different services (= simulated/executed processes, currently ovs, ryu and wireguard)
- Support different network setup types (VxLan from distrinet, 1on1 network for a real environment)

Solution:
Use one configuration builder per node which generates commands and assets. Export the resulting configuration
either to a bash script or execute it remotely via ssh.

Testing capabilities:
Due to the json export of the topology, one can automatically connect to remote servers using ssh (like distrinet)
and perform traffic testing and monitoring there. This could also be done automatically by a script. More on that coming
soon.

Time plan:

- 13.6.-14.6. Polish new topology implementation
- 15.6.-17.6. Build the configuration builder for linux servers from the original testbed
- 20.6. Build the file configuration exporter (indirect configuration)
- 21.6. Build remote ssh capabilities for testing
- 22.6. Build the ssh configuration exporter (direct configuration)
- 23.6.+ Start implementing the test utilities (to be planned)