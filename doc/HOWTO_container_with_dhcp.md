# Container with DHCP

Create a new profile for all containers that should be connected to hosts network.
The container will not be reachable from the host itself, but integrate itself as a
separate machine in the LAN the host is part of by using macvlan.
```shell
lxc profile create macvlan
```

In the profile we add a new default network device that references our main
network device of our host to access the LAN with:
```shell
lxc profile device add macvlan eth0 nic nictype=macvlan parent=enp2s0
```

Then we can create new containers using this configuration:
```shell
lxc launch <image> <container_name> --profile default --profile macvlan
```

If we do not already have an ip assigned to device `eth0` inside the container,
we need to obtain a dhcp lease from our LAN router:
```shell
lxc exec <container_name> -- dhclient
```

Now the container should be able to access the LAN and beyond. This is required to install
packages inside an container, for example.