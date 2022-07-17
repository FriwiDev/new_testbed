from ipaddress import ip_address

from config.configuration import Configuration, Command
from network.network_implementation import NetworkImplementation
from network.network_utils import NetworkUtils
from topo.node import Node, NodeType
from topo.subnet import Subnet


class VxLanNetworkImplementation(NetworkImplementation):
    def __init__(self, multicast_ip: ip_address, vxlan_id: int = 42):
        self.topo = None
        self.multicast_ip = multicast_ip
        self.vxlan_id = vxlan_id
        self.local_subnet = Subnet("192.168.128.0/17")

    def configure(self, topo: 'Topo'):
        # Not really anything to configure before generating the actual config. Everything is deterministic here.
        self.topo = topo

    def generate(self, node: Node, config: Configuration):
        if node.type is not NodeType.LINUX_DEBIAN and node.type is not NodeType.LINUX_ARCH:
            raise Exception("VxLan currently only supports configuring LinuxNodes")

        # TODO Add mac addresses to devices (implementation dependent on container/namespace)

        br_num = 0

        # Iterate over links
        for link in self.topo.links:
            if link.service1.executor == node or link.service2.executor == node:
                # We participate
                if link.service1.executor == node and link.service2.executor == node:
                    # We are the only participant -> route internally
                    # Create two bridges on which the services can bind
                    if link.intf1.bind_name is None:
                        link.intf1.bind_name = f"vbr{br_num}"
                        br_num += 1
                    if link.intf2.bind_name is None:
                        link.intf2.bind_name = f"vbr{br_num}"
                        br_num += 1
                    # Create veth link
                    config.add_command(
                        Command(f"ip link add {link.intf1.bind_name} type veth peer {link.intf2.bind_name}"),
                        Command(f"ip link del {link.intf1.bind_name}"))
                    # Set all devices up
                    NetworkUtils.set_up(config, link.intf1.bind_name)
                    NetworkUtils.set_up(config, link.intf2.bind_name)
                else:
                    # We only manage one end -> route via vxlan
                    intf = link.intf1 if link.service1.executor == node else link.intf2
                    if intf.bind_name is None:
                        intf.bind_name = f"br{br_num}"
                        br_num += 1
                    # Create one bridge on which the service can bind
                    config.add_command(Command(f"brctl addbr {intf.bind_name}"),
                                       Command(f"brctl delbr {intf.bind_name}"))
                    # Create vxlan device used for this service
                    # TODO Make enp3s0 configurable
                    config.add_command(
                        Command(f"ip link add vx-{intf.bind_name} type vxlan id {self.vxlan_id} "
                                f"group {self.multicast_ip} dev enp3s0"),
                        Command(f"ip link del vx-{intf.bind_name}"))
                    self.vxlan_id += 1
                    # Add vxlan device to our bridge
                    config.add_command(Command(f"brctl addif {intf.bind_name} vx-{intf.bind_name}"),
                                       Command(f"brctl delif {intf.bind_name} vx-{intf.bind_name}"))
                    # Set all devices up
                    NetworkUtils.set_up(config, intf.bind_name)
                    NetworkUtils.set_up(config, "vx-" + intf.bind_name)
                    # TODO Routing in our bridge


    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(NetworkImplementation).to_dict(), **{
            'multicast_ip': str(self.multicast_ip),
            'vxlan_id': self.vxlan_id
        }}

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'VxLanNetworkImplementation':
        """Internal method to initialize from dictionary."""
        ret = VxLanNetworkImplementation(ip_address(in_dict['multicast_ip']),
                                         int(in_dict['vxlan_id']))
        return ret
