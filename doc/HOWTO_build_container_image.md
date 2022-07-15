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
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/
lxc init ubuntu-minimal ryu --profile default --profile macvlan
lxc start ryu
lxc exec ryu -- apt update
lxc exec ryu -- apt upgrade -y
lxc exec ryu -- apt install -y python3-ryu
lxc exec ryu -- apt clean
lxc exec ryu -- apt autoremove -y
lxc stop ryu
lxc config edit ryu # Edit config and remove macvlan profile
lxc start ryu
lxc stop ryu
lxc snapshot ryu snap1
lxc publish ryu/snap1 --alias ryu --public
lxc image export ryu img/ryu-ubuntu-18.04-minimal
```

### OpenVSwitch
```shell
lxc remote add --protocol simplestreams ubuntu-minimal https://cloud-images.ubuntu.com/minimal/releases/
lxc init ubuntu-minimal ovs --profile default --profile macvlan
lxc start ovs
lxc exec ovs -- apt update
lxc exec ovs -- apt upgrade -y
sysctl kernel.dmesg_restrict=0 # OVS installer uses dmesg in container
lxc exec ovs -- apt install -y openvswitch-switch
sysctl kernel.dmesg_restrict=1
lxc exec ovs -- apt clean
lxc exec ovs -- apt autoremove -y
lxc stop ovs
lxc config edit ovs # Edit config and remove macvlan profile
lxc start ovs
lxc stop ovs
lxc snapshot ovs snap1
lxc publish ovs/snap1 --alias ovs --public
lxc image export ovs img/ovs-ubuntu-18.04-minimal
```