from ipaddress import ip_address

from config.configuration import Configuration, Command
from network.network_implementation import NetworkImplementation
from topo.node import Node, NodeType


class VxLanNetworkImplementation(NetworkImplementation):
    def __init__(self, multicast_ip: ip_address, vxlan_id: int = 42, device_name: str = "vx0",
                 bridge_name: str = "br0"):
        self.topo = None
        self.multicast_ip = multicast_ip
        self.vxlan_id = vxlan_id
        self.device_name = device_name
        self.bridge_name = bridge_name

    def configure(self, topo: 'Topo'):
        # Not really anything to configure before generating the actual config. Everything is deterministic here.
        self.topo = topo

    def generate(self, node: Node, config: Configuration):
        if node.type is not NodeType.LINUX_DEBIAN and node.type is not NodeType.LINUX_ARCH:
            raise Exception("VxLan currently only supports configuring LinuxNodes")
        # TODO Make eth0 configurable
        # Add vxlan interface on node
        config.add_command(
            Command(f"ip link add {self.device_name} type vxlan id {self.vxlan_id} group {self.multicast_ip} dev eth0"),
            Command(f"ip link del {self.device_name}"))
        # Add a bridge to the vxlan interface
        config.add_command(
            Command(f"brctl addbr {self.bridge_name}; brctl addif {self.bridge_name} {self.device_name}"),
            Command(f"brctl delif {self.bridge_name} {self.device_name}; brctl delbr {self.bridge_name}"))
        gen = 0
        # Add one device per service
        for _, service in self.topo.services.items():
            if service.executor is node:
                # Netns name
                service_data = ("netns-" + service.name, "make_me_a_tuple_for_now")
                config.add_command(Command(f"ip netns add {service_data[0]}"),
                                   Command(f"ip netns del {service_data[0]}"))
                for intf in service.intfs:
                    # Outer dev name, Inner dev name, ip addresses, ip networks, mac address
                    interface_data = (f"veth{gen}", intf.name, intf.ips, intf.networks,
                                      # Used to be f"veth-{service.name}-{intf.name}" as name
                                      intf.mac_address)
                    gen += 1
                    # Create veth pair
                    config.add_command(Command(f"ip link add {interface_data[0]} master br0 type veth "
                                               f"peer {interface_data[1]} netns {service_data[0]}"),
                                       Command(f"ip link del {interface_data[0]}; "
                                               f"ip netns exec {service_data[0]} ip link del {interface_data[1]}"))
                    # Add mac address to (outer) device
                    config.add_command(Command(f"ip link set dev {interface_data[0]} address {interface_data[4]}"),
                                       Command())
                    # For each configured ip address, configure both devices
                    for i in range(0, len(interface_data[2])):
                        config.add_command(Command(f"ip addr add "
                                                   f"{str(interface_data[2][i])}/{str(interface_data[3][i].prefixlen)} "
                                                   f"dev {interface_data[0]}"),
                                           Command(f"ip addr del "
                                                   f"{str(interface_data[2][i])}/{str(interface_data[3][i].prefixlen)} "
                                                   f"dev {interface_data[0]}"))
                        config.add_command(Command(f"ip netns exec {service_data[0]} ip addr add "
                                                   f"{str(interface_data[2][i])}/{str(interface_data[3][i].prefixlen)} "
                                                   f"dev {interface_data[1]}"),
                                           Command(f"ip netns exec {service_data[0]} ip addr del "
                                                   f"{str(interface_data[2][i])}/{str(interface_data[3][i].prefixlen)} "
                                                   f"dev {interface_data[1]}"))
                    # Set veth pair up
                    config.add_command(Command(f"ip link set dev {interface_data[0]} up; "
                                               f"ip netns exec {service_data[0]} "
                                               f"ip link set dev {interface_data[1]} up"),
                                       Command(f"ip link set dev {interface_data[0]} down; "
                                               f"ip netns exec {service_data[0]} "
                                               f"ip link set dev {interface_data[1]} down"))
        # Set bridge and vxlan device up
        config.add_command(Command(f"ip link set dev {self.device_name} up; "
                                   f"ip link set dev {self.bridge_name} up"),
                           Command(f"ip link set dev {self.bridge_name} down; "
                                   f"ip link set dev {self.device_name} down"))

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(NetworkImplementation).to_dict(), **{
            'multicast_ip': str(self.multicast_ip),
            'vxlan_id': self.vxlan_id,
            'device_name': self.device_name,
            'bridge_name': self.bridge_name
        }}

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'VxLanNetworkImplementation':
        """Internal method to initialize from dictionary."""
        ret = VxLanNetworkImplementation(ip_address(in_dict['multicast_ip']),
                                         int(in_dict['vxlan_id']),
                                         in_dict['device_name'],
                                         in_dict['bridge_name'])
        return ret
