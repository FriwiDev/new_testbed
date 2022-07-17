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

### Importing images
```bash
wget https://friwi.me/testbed_img/ovs-ubuntu-18.04-minimal.tar.gz
wget https://friwi.me/testbed_img/ryu-ubuntu-18.04-minimal.tar.gz
wget https://friwi.me/testbed_img/simple-host-ubuntu-18.04-minimal.tar.gz
lxc image import ovs-ubuntu-18.04-minimal.tar.gz --alias ovs --public
lxc image import ryu-ubuntu-18.04-minimal.tar.gz --alias ryu --public
lxc image import simple-host-ubuntu-18.04-minimal.tar.gz --alias simple-host --public```