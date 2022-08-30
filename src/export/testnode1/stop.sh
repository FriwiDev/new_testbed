#!/bin/bash

echo "lxc exec controller1 -- killall ryu-manager"
lxc exec controller1 -- killall ryu-manager
echo ""

echo "lxc exec controller1 --  ip route del 10.0.0.3"
lxc exec controller1 --  ip route del 10.0.0.3
echo "lxc exec controller1 --  ip addr del dev testnode1-eth0 10.0.0.2/24"
lxc exec controller1 --  ip addr del dev testnode1-eth0 10.0.0.2/24
echo "lxc exec controller1 --  ip link set dev testnode1-eth0 down"
lxc exec controller1 --  ip link set dev testnode1-eth0 down
echo ""

echo "lxc network detach br0 controller1 testnode1-eth0"
lxc network detach br0 controller1 testnode1-eth0
echo "lxc stop controller1"
lxc stop controller1
echo "lxc rm controller1"
lxc rm controller1
echo "tc qdisc remove dev vx-br0 root netem"
tc qdisc remove dev vx-br0 root netem
echo "ip link set dev vx-br0 down"
ip link set dev vx-br0 down
echo "ip link set dev br0 down"
ip link set dev br0 down
echo "brctl delif br0 vx-br0"
brctl delif br0 vx-br0
echo "ip link del vx-br0"
ip link del vx-br0
echo "brctl delbr br0"
brctl delbr br0
