#!/bin/bash
set -e

echo "brctl addbr br0"
brctl addbr br0
echo "ip link add vx-br0 type vxlan id 42 group 239.1.1.1 dev eth0"
ip link add vx-br0 type vxlan id 42 group 239.1.1.1 dev eth0
echo "brctl addif br0 vx-br0"
brctl addif br0 vx-br0
echo "ip link set dev br0 up"
ip link set dev br0 up
echo "ip link set dev vx-br0 up"
ip link set dev vx-br0 up
echo "tc qdisc add dev vx-br0 root netem delay 100 30 35.0% loss 25.0% 35.0%"
tc qdisc add dev vx-br0 root netem delay 100 30 35.0% loss 25.0% 35.0%
echo "lxc init ryu controller1"
lxc init ryu controller1
echo "lxc start controller1"
lxc start controller1
echo "lxc network attach br0 controller1 testnode1-eth0 testnode1-eth0"
lxc network attach br0 controller1 testnode1-eth0 testnode1-eth0
echo "lxc exec controller1 --  ip link set dev testnode1-eth0 address 00:00:00:00:08:15"
lxc exec controller1 --  ip link set dev testnode1-eth0 address 00:00:00:00:08:15
echo "lxc exec controller1 --  ip link set dev testnode1-eth0 up"
lxc exec controller1 --  ip link set dev testnode1-eth0 up
echo "lxc exec controller1 --  ip addr add dev testnode1-eth0 10.0.0.2/24"
lxc exec controller1 --  ip addr add dev testnode1-eth0 10.0.0.2/24
echo "lxc exec controller1 --  ip route add 10.0.0.3 via 10.0.0.2"
lxc exec controller1 --  ip route add 10.0.0.3 via 10.0.0.2
echo "lxc file push $(pwd)/defaults/simple_switch.py controller1/tmp/"
lxc file push $(pwd)/defaults/simple_switch.py controller1/tmp/
echo "lxc exec controller1 -- ryu-manager --verbose /tmp/simple_switch.py &> /tmp/controller_controller1.log &"
lxc exec controller1 -- ryu-manager --verbose /tmp/simple_switch.py &> /tmp/controller_controller1.log &
