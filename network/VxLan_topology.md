# VxLan topology

+ Consists of only linux nodes
+ One node may have multiple services
+ No external services (on other non-linux nodes) supported

## Sketch
One node looks like this:
```
MAIN NETNS                         | SERVICE NETNS (one per service)
                                   |
                       -> veth00 <-|-> veth01
eth0 <-> vx0 <-> br0 <-            | 
                       -> veth10 <-|-> veth11
                                   | 
```
TODO: Convert to nicer svg graphic

Where:

+ eth0 is the outgoing network interface on the node
+ vx0 is the vlan interface, emitting multicast traffic towards eth0
+ br0 is the bridge holding the network together
+ (veth00, veth01) and (veth10, veth11) are veth pairs providing interfaces for the services according to their configuration