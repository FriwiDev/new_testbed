from ipaddress import ip_address, ip_network

from config.configuration import Configuration, Command
from network.network_implementation import NetworkImplementation
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
                        link.intf1.bind_name = f"br{br_num}"
                        br_num += 1
                    if link.intf2.bind_name is None:
                        link.intf2.bind_name = f"br{br_num}"
                        br_num += 1
                    config.add_command(Command(f"brctl addbr {link.intf1.bind_name}"),
                                       Command(f"brctl delbr {link.intf1.bind_name}"))
                    config.add_command(Command(f"brctl addbr {link.intf2.bind_name}"),
                                       Command(f"brctl delbr {link.intf2.bind_name}"))
                    # Create veth link between our bridges
                    config.add_command(Command(f"ip link add veth-{link.intf1.bind_name} type veth peer veth-{link.intf2.bind_name}"),
                                       Command(f"ip link del veth-{link.intf1.bind_name}"))
                    # Attach veth links to their bridges
                    config.add_command(Command(f"brctl addif {link.intf1.bind_name} veth-{link.intf1.bind_name}"),
                                       Command(f"brctl delif {link.intf1.bind_name} veth-{link.intf1.bind_name}"))
                    config.add_command(Command(f"brctl addif {link.intf2.bind_name} veth-{link.intf2.bind_name}"),
                                       Command(f"brctl delif {link.intf2.bind_name} veth-{link.intf2.bind_name}"))
                    # Set all devices up
                    VxLanNetworkImplementation._set_up(config, link.intf1.bind_name)
                    VxLanNetworkImplementation._set_up(config, link.intf2.bind_name)
                    VxLanNetworkImplementation._set_up(config, "veth-"+link.intf1.bind_name)
                    VxLanNetworkImplementation._set_up(config, "veth-" + link.intf2.bind_name)
                    # Assign local ips
                    intf1_ip = self.local_subnet.generate_next_ip()
                    intf2_ip = self.local_subnet.generate_next_ip()
                    veth1_ip = self.local_subnet.generate_next_ip()
                    veth2_ip = self.local_subnet.generate_next_ip()
                    VxLanNetworkImplementation._add_ip(config, link.intf1.bind_name, intf1_ip,
                                                       self.local_subnet.network)
                    VxLanNetworkImplementation._add_ip(config, link.intf2.bind_name, intf2_ip,
                                                       self.local_subnet.network)
                    VxLanNetworkImplementation._add_ip(config, "veth-"+link.intf1.bind_name, veth1_ip,
                                                       self.local_subnet.network)
                    VxLanNetworkImplementation._add_ip(config, "veth-"+link.intf2.bind_name, veth2_ip,
                                                       self.local_subnet.network)
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
                    VxLanNetworkImplementation._set_up(config, intf.bind_name)
                    VxLanNetworkImplementation._set_up(config, "vx-"+intf.bind_name)
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

    @classmethod
    def _set_up(cls, config: 'Configuration', device_name: str):
        config.add_command(Command(f"ip link set dev {device_name} up"),
                           Command(f"ip link set dev {device_name} down"))
        pass

    @classmethod
    def _add_ip(cls, config: 'Configuration', device_name: str, ip: ip_address, network: ip_network):
        config.add_command(Command(f"ip addr add dev {device_name} {str(ip)}/{str(network.prefixlen)}"),
                           Command(f"ip addr del dev {device_name} {str(ip)}/{str(network.prefixlen)}"))
        pass

    @classmethod
    def _add_route(cls, config: 'Configuration', ip: ip_address, via_ip: ip_address, via_network: ip_network):
        config.add_command(Command(f"ip route add {str(ip)} {str(via_ip)}/{str(via_network.prefixlen)}"),
                           Command(f"ip route del {str(ip)}"))
        pass
