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
echo "ip link add vbr1 type veth peer vbr2"
ip link add vbr1 type veth peer vbr2
echo "ip link set dev vbr1 up"
ip link set dev vbr1 up
echo "ip link set dev vbr2 up"
ip link set dev vbr2 up
echo "ip link add vbr3 type veth peer vbr4"
ip link add vbr3 type veth peer vbr4
echo "ip link set dev vbr3 up"
ip link set dev vbr3 up
echo "ip link set dev vbr4 up"
ip link set dev vbr4 up
echo "lxc init ovs switch1"
lxc init ovs switch1
echo "lxc start switch1"
lxc start switch1
echo "lxc network attach br0 switch1 testnode-eth0 testnode-eth0"
lxc network attach br0 switch1 testnode-eth0 testnode-eth0
echo "lxc exec switch1 --  ip link set dev testnode-eth0 address 00:00:00:00:08:16"
lxc exec switch1 --  ip link set dev testnode-eth0 address 00:00:00:00:08:16
echo "lxc exec switch1 --  ip link set dev testnode-eth0 up"
lxc exec switch1 --  ip link set dev testnode-eth0 up
echo "lxc exec switch1 --  ip addr add dev testnode-eth0 10.0.0.3/24"
lxc exec switch1 --  ip addr add dev testnode-eth0 10.0.0.3/24
echo "lxc network attach vbr2 switch1 testnode-eth2 testnode-eth2"
lxc network attach vbr2 switch1 testnode-eth2 testnode-eth2
echo "lxc exec switch1 --  ip link set dev testnode-eth2 address 00:00:00:00:08:18"
lxc exec switch1 --  ip link set dev testnode-eth2 address 00:00:00:00:08:18
echo "lxc exec switch1 --  ip link set dev testnode-eth2 up"
lxc exec switch1 --  ip link set dev testnode-eth2 up
echo "lxc exec switch1 --  ip addr add dev testnode-eth2 10.0.0.5/24"
lxc exec switch1 --  ip addr add dev testnode-eth2 10.0.0.5/24
echo "lxc network attach vbr4 switch1 testnode-eth4 testnode-eth4"
lxc network attach vbr4 switch1 testnode-eth4 testnode-eth4
echo "lxc exec switch1 --  ip link set dev testnode-eth4 address 00:00:00:00:08:1a"
lxc exec switch1 --  ip link set dev testnode-eth4 address 00:00:00:00:08:1a
echo "lxc exec switch1 --  ip link set dev testnode-eth4 up"
lxc exec switch1 --  ip link set dev testnode-eth4 up
echo "lxc exec switch1 --  ip addr add dev testnode-eth4 10.0.0.7/24"
lxc exec switch1 --  ip addr add dev testnode-eth4 10.0.0.7/24
echo "lxc exec switch1 --  ip route add 10.0.0.2 via 10.0.0.3"
lxc exec switch1 --  ip route add 10.0.0.2 via 10.0.0.3
echo "lxc exec switch1 --  ip route add 10.0.0.4 via 10.0.0.5"
lxc exec switch1 --  ip route add 10.0.0.4 via 10.0.0.5
echo "lxc exec switch1 --  ip route add 10.0.0.6 via 10.0.0.7"
lxc exec switch1 --  ip route add 10.0.0.6 via 10.0.0.7
echo "lxc exec switch1 -- service openvswitch-switch stop"
lxc exec switch1 -- service openvswitch-switch stop
echo "lxc exec switch1 -- service ovs-vswitchd stop"
lxc exec switch1 -- service ovs-vswitchd stop
echo "lxc exec switch1 -- service ovsdb-server stop"
lxc exec switch1 -- service ovsdb-server stop
echo "lxc exec switch1 -- rm -rf /var/run/openvswitch"
lxc exec switch1 -- rm -rf /var/run/openvswitch
echo "lxc exec switch1 -- mkdir /var/run/openvswitch"
lxc exec switch1 -- mkdir /var/run/openvswitch
echo "lxc exec switch1 -- ovsdb-server --remote=punix:/var/run/openvswitch/db.sock --remote=db:Open_vSwitch,Open_vSwitch,manager_options --private-key=db:Open_vSwitch,SSL,private_key --certificate=db:Open_vSwitch,SSL,certificate --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert --log-file=/var/log/openvswitch/ovsdb-server.log --pidfile --verbose --detach"
lxc exec switch1 -- ovsdb-server --remote=punix:/var/run/openvswitch/db.sock --remote=db:Open_vSwitch,Open_vSwitch,manager_options --private-key=db:Open_vSwitch,SSL,private_key --certificate=db:Open_vSwitch,SSL,certificate --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert --log-file=/var/log/openvswitch/ovsdb-server.log --pidfile --verbose --detach
echo "lxc exec switch1 -- ovs-vsctl init"
lxc exec switch1 -- ovs-vsctl init
echo "lxc exec switch1 -- ovs-vswitchd --pidfile --detach"
lxc exec switch1 -- ovs-vswitchd --pidfile --detach
echo "lxc exec switch1 -- ovs-vsctl -- --id=@switch1controller1 create Controller target=\"tcp:10.0.0.2:6653\" max_backoff=1000 -- --if-exists del-br switch1 -- add-br switch1 -- set bridge switch1 controller=[@switch1controller1] other_config:datapath-id=0000000000000001 fail_mode=secure other-config:disable-in-band=true other-config:dp-desc=switch1 -- add-port switch1 testnode-eth2 -- add-port switch1 testnode-eth4"
lxc exec switch1 -- ovs-vsctl -- --id=@switch1controller1 create Controller target=\"tcp:10.0.0.2:6653\" max_backoff=1000 -- --if-exists del-br switch1 -- add-br switch1 -- set bridge switch1 controller=[@switch1controller1] other_config:datapath-id=0000000000000001 fail_mode=secure other-config:disable-in-band=true other-config:dp-desc=switch1 -- add-port switch1 testnode-eth2 -- add-port switch1 testnode-eth4
echo "lxc exec switch1 -- ip link set dev switch1 up"
lxc exec switch1 -- ip link set dev switch1 up
echo "lxc init simple-host host1"
lxc init simple-host host1
echo "lxc start host1"
lxc start host1
echo "lxc network attach vbr1 host1 testnode-eth1 testnode-eth1"
lxc network attach vbr1 host1 testnode-eth1 testnode-eth1
echo "lxc exec host1 --  ip link set dev testnode-eth1 address 00:00:00:00:08:17"
lxc exec host1 --  ip link set dev testnode-eth1 address 00:00:00:00:08:17
echo "lxc exec host1 --  ip link set dev testnode-eth1 up"
lxc exec host1 --  ip link set dev testnode-eth1 up
echo "lxc exec host1 --  ip addr add dev testnode-eth1 10.0.0.4/24"
lxc exec host1 --  ip addr add dev testnode-eth1 10.0.0.4/24
echo "lxc exec host1 --  ip route add 10.0.0.5 via 10.0.0.4"
lxc exec host1 --  ip route add 10.0.0.5 via 10.0.0.4
echo "lxc exec host1 --  ip route add 10.0.0.6 via 10.0.0.4"
lxc exec host1 --  ip route add 10.0.0.6 via 10.0.0.4
echo "lxc init simple-host host2"
lxc init simple-host host2
echo "lxc start host2"
lxc start host2
echo "lxc network attach vbr3 host2 testnode-eth3 testnode-eth3"
lxc network attach vbr3 host2 testnode-eth3 testnode-eth3
echo "lxc exec host2 --  ip link set dev testnode-eth3 address 00:00:00:00:08:19"
lxc exec host2 --  ip link set dev testnode-eth3 address 00:00:00:00:08:19
echo "lxc exec host2 --  ip link set dev testnode-eth3 up"
lxc exec host2 --  ip link set dev testnode-eth3 up
echo "lxc exec host2 --  ip addr add dev testnode-eth3 10.0.0.6/24"
lxc exec host2 --  ip addr add dev testnode-eth3 10.0.0.6/24
echo "lxc exec host2 --  ip route add 10.0.0.7 via 10.0.0.6"
lxc exec host2 --  ip route add 10.0.0.7 via 10.0.0.6
echo "lxc exec host2 --  ip route add 10.0.0.4 via 10.0.0.6"
lxc exec host2 --  ip route add 10.0.0.4 via 10.0.0.6
