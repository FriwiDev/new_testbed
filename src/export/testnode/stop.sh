#!/bin/bash

echo "lxc exec host2 --  ip route del 10.0.0.4"
lxc exec host2 --  ip route del 10.0.0.4
echo "lxc exec host2 --  ip route del 10.0.0.7"
lxc exec host2 --  ip route del 10.0.0.7
echo "lxc exec host2 --  ip addr del dev testnode-eth3 10.0.0.6/24"
lxc exec host2 --  ip addr del dev testnode-eth3 10.0.0.6/24
echo "lxc exec host2 --  ip link set dev testnode-eth3 down"
lxc exec host2 --  ip link set dev testnode-eth3 down
echo ""

echo "lxc network detach vbr3 host2 testnode-eth3"
lxc network detach vbr3 host2 testnode-eth3
echo "lxc stop host2"
lxc stop host2
echo "lxc rm host2"
lxc rm host2
echo "lxc exec host1 --  ip route del 10.0.0.6"
lxc exec host1 --  ip route del 10.0.0.6
echo "lxc exec host1 --  ip route del 10.0.0.5"
lxc exec host1 --  ip route del 10.0.0.5
echo "lxc exec host1 --  ip addr del dev testnode-eth1 10.0.0.4/24"
lxc exec host1 --  ip addr del dev testnode-eth1 10.0.0.4/24
echo "lxc exec host1 --  ip link set dev testnode-eth1 down"
lxc exec host1 --  ip link set dev testnode-eth1 down
echo ""

echo "lxc network detach vbr1 host1 testnode-eth1"
lxc network detach vbr1 host1 testnode-eth1
echo "lxc stop host1"
lxc stop host1
echo "lxc rm host1"
lxc rm host1
echo "lxc exec switch1 -- ip link set dev switch1 down"
lxc exec switch1 -- ip link set dev switch1 down
echo "lxc exec switch1 -- ovs-vsctl del-br switch1"
lxc exec switch1 -- ovs-vsctl del-br switch1
echo ""

echo ""

echo ""

echo ""

echo ""

echo ""

echo ""

echo ""

echo "lxc exec switch1 --  ip route del 10.0.0.6"
lxc exec switch1 --  ip route del 10.0.0.6
echo "lxc exec switch1 --  ip route del 10.0.0.4"
lxc exec switch1 --  ip route del 10.0.0.4
echo "lxc exec switch1 --  ip route del 10.0.0.2"
lxc exec switch1 --  ip route del 10.0.0.2
echo "lxc exec switch1 --  ip addr del dev testnode-eth4 10.0.0.7/24"
lxc exec switch1 --  ip addr del dev testnode-eth4 10.0.0.7/24
echo "lxc exec switch1 --  ip link set dev testnode-eth4 down"
lxc exec switch1 --  ip link set dev testnode-eth4 down
echo ""

echo "lxc network detach vbr4 switch1 testnode-eth4"
lxc network detach vbr4 switch1 testnode-eth4
echo "lxc exec switch1 --  ip addr del dev testnode-eth2 10.0.0.5/24"
lxc exec switch1 --  ip addr del dev testnode-eth2 10.0.0.5/24
echo "lxc exec switch1 --  ip link set dev testnode-eth2 down"
lxc exec switch1 --  ip link set dev testnode-eth2 down
echo ""

echo "lxc network detach vbr2 switch1 testnode-eth2"
lxc network detach vbr2 switch1 testnode-eth2
echo "lxc exec switch1 --  ip addr del dev testnode-eth0 10.0.0.3/24"
lxc exec switch1 --  ip addr del dev testnode-eth0 10.0.0.3/24
echo "lxc exec switch1 --  ip link set dev testnode-eth0 down"
lxc exec switch1 --  ip link set dev testnode-eth0 down
echo ""

echo "lxc network detach br0 switch1 testnode-eth0"
lxc network detach br0 switch1 testnode-eth0
echo "lxc stop switch1"
lxc stop switch1
echo "lxc rm switch1"
lxc rm switch1
echo "ip link set dev vbr4 down"
ip link set dev vbr4 down
echo "ip link set dev vbr3 down"
ip link set dev vbr3 down
echo "ip link del vbr3"
ip link del vbr3
echo "ip link set dev vbr2 down"
ip link set dev vbr2 down
echo "ip link set dev vbr1 down"
ip link set dev vbr1 down
echo "ip link del vbr1"
ip link del vbr1
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
