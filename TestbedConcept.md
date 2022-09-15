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
File       SSH
Config     Config
Exporter   Exporter
```

Goals:

- Implement topology structure close to original distrinet to enable quick reuse of already implemented types
- Topology structures can be saved and loaded from json as a reference for future script executions
- Remove requirement of central host which manages the network (in comparison to distrinet)
- Support different node (= real hardware device) types, like servers or switches to be integrated
- Support different services (= simulated/executed processes, currently ovs, ryu and normal host)
- Support different network setup types (VxLan from distrinet, 1on1 network for a real environment)

Solution:
Use one configuration builder per node which generates commands and assets. Export the resulting configuration
either to a bash script or execute it remotely via ssh.

Testing capabilities:
Due to the json export of the topology, one can automatically connect to remote servers using ssh (like distrinet)
and perform traffic testing and monitoring there. This could also be done automatically by a script. More on that coming
soon.

# Current todo
- Extensive testing
- Documentation (when everything is polished)
- Control network (macvlan + ssh)
- Make generation script robuster

# Optional features
- MacVlan mode with resolving via hostname
- Gui to visualize network structure and live monitor traffic, statistics like ping
    and network configuration. Could also be used to automatically execute scipts
    so the only real coding part left is creating the topology scripts.

# Done
- Own class to launch a wireguard instance as easy as possible (low effort)
- Find out why suddenly traffic does not pass through ovs anymore even though there
    is no controller specified and mode is standalone (not `secure`). When monitoring
    traffic with `ovs-ofctl dump-ports <ovsbridge>`, arp traffic seems to be passing
    one way, returning to the switch from the other side and then not matching the flow.
    This seems a bit weird and will most likely need some debugging time :/.
    Maybe Amr has more experience with ovs and can help?