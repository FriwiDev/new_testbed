# Building a minimal container image

To build a container image with minimal packages and one specific network component,
you will first need to create a container with a minimal linux distro.

For example, you can create a container with Ubuntu:
```shell
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/
lxc init ubuntu-minimal <container_name> --profile default --profile macvlan
```
You can find information on where the macvlan profile is coming from [here](HOWTO_container_with_dhcp.md).

Then you can fire up your container and start setting up the environment that you
want to put in the image.
```shell
lxc start <container_name>
lxc exec <container_name> -- <your_command_inside_of_container>
# ...
```

After you set up everything inside the container, it is time to export the container
to an image.
```shell
# Clear the apt cache on debian based systems (to make the image smaller)
lxc exec <container_name> -- apt clean
# ...and autoremove packages
lxc exec <container_name> -- apt autoremove
# Detach the container from the hosts LAN (when using macvlan profile from above)
lxc stop <container_name> #Stop container
lxc config edit ryu # Edit config and remove macvlan profile
lxc start <container_name> # Start container again to remove potentially cached network device
# Stop the container
lxc stop <container_name>
# Create a snapshot of the container
lxc snapshot <container_name> <snapshot_name>
# Publish a new image from our snapshot
lxc publish <container_name>/<snapshot_name> --alias <image_name>  --public
# Export our image to a Gzipped tarball (path without .tar.gz)
lxc image export <image_name> <path>
```

Now you can distribute the image inside the tarball and import the image anywhere with
(path optionally with .tar.gz):
```shell
lxc import <path> --alias <image_name> --public
```

## Examples

Here are two examples for ryu and openvswitch.

### Ryu Controller
```shell
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/ || true
lxc init ubuntu-minimal:focal ryu --profile default --profile macvlan
lxc start ryu
sleep 3 #Allow container to perform dhcp and establish a connection
lxc exec ryu -- apt update
lxc exec ryu -- apt upgrade -y
lxc exec ryu -- apt install -y iputils-ping net-tools iperf3 python3-ryu wireguard tcpdump ifstat
# Install ovs-common to have ovs-ofctl command
lxc exec ryu -- apt install -y openvswitch-common || true # Installation will fail due to hostname service :/
lxc exec ryu -- apt clean
lxc exec ryu -- apt autoremove -y
lxc stop ryu
lxc profile remove ryu macvlan
lxc start ryu
lxc stop ryu
lxc snapshot ryu snap1
lxc publish ryu/snap1 --alias ryu --public
lxc image export ryu img/ryu-ubuntu-20.04-minimal
lxc rm ryu
```

### OpenVSwitch

```shell
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/ || true
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
lxc publish ovs/snap1 --alias ovs --public
lxc image export ovs img/ovs-ubuntu-20.04-minimal
lxc rm ovs
```

### Basic host

```shell
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/ || true
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
lxc publish simple-host/snap1 --alias simple-host --public
lxc image export simple-host img/simple-host-ubuntu-20.04-minimal
lxc rm simple-host
```
