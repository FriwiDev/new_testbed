#!/bin/bash
set -e

# Build ryu
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/ || true
lxc rm -f ryu || true
lxc init ubuntu-minimal:focal ryu --profile default --profile macvlan
lxc start ryu
sleep 3 #Allow container to perform dhcp and establish a connection
lxc exec ryu -- apt update
lxc exec ryu -- apt upgrade -y
lxc exec ryu -- apt install -y iputils-ping net-tools iperf3 python3-ryu wireguard tcpdump ifstat
lxc exec ryu -- apt clean
lxc exec ryu -- apt autoremove -y
lxc stop ryu
lxc profile remove ryu macvlan
lxc start ryu
lxc stop ryu
lxc snapshot ryu snap1
lxc publish ryu/snap1 --public
lxc image export ryu img/ryu-ubuntu-20.04-minimal
lxc rm ryu

# Build ovs
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/ || true
lxc rm -f ovs || true
lxc init ubuntu-minimal:focal ovs --profile default --profile macvlan
lxc start ovs
sleep 3 #Allow container to perform dhcp and establish a connection
lxc exec ovs -- apt update
lxc exec ovs -- apt upgrade -y
sysctl -w kernel.dmesg_restrict=0 # OVS installer uses dmesg in container
lxc exec ovs -- apt install -y iputils-ping net-tools iperf3 wireguard tcpdump ifstat
lxc exec ovs -- apt install -y openvswitch-switch || true # Installation will fail due to hostname service :/
lxc exec ovs -- rm /etc/systemd/system/openvswitch-switch.service.requires/ovs-record-hostname.service # remove requirement
lxc exec ovs -- systemctl disable openvswitch-switch.service
sysctl -w kernel.dmesg_restrict=1
lxc exec ovs -- apt clean
lxc exec ovs -- apt autoremove -y
lxc stop ovs
lxc profile remove ovs macvlan
lxc start ovs
lxc stop ovs
lxc snapshot ovs snap1
lxc publish ovs/snap1 --public
lxc image export ovs img/ovs-ubuntu-20.04-minimal
lxc rm ovs

# Build simple host
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/ || true
lxc rm -f simple-host || true
lxc init ubuntu-minimal:focal simple-host --profile default --profile macvlan
lxc start simple-host
sleep 3 #Allow container to perform dhcp and establish a connection
lxc exec simple-host -- apt update
lxc exec simple-host -- apt upgrade -y
lxc exec simple-host -- apt install -y iputils-ping net-tools iperf3 wireguard tcpdump ifstat
lxc exec simple-host -- apt clean
lxc exec simple-host -- apt autoremove -y
lxc stop simple-host
lxc profile remove simple-host macvlan
lxc start simple-host
lxc stop simple-host
lxc snapshot simple-host snap1
lxc publish simple-host/snap1 --public
lxc image export simple-host img/simple-host-ubuntu-20.04-minimal
lxc rm simple-host

