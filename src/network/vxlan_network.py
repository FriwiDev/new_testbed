from ipaddress import ip_address, ip_network

from config.configuration import Configuration, Command
from network.network_address_generator import BasicNetworkAddressGenerator
from network.network_implementation import NetworkImplementation
from network.network_utils import NetworkUtils
from topo.node import Node, NodeType
from topo.util import ClassUtil


class VxLanNetworkImplementation(NetworkImplementation):
    def __init__(self, network: ip_network or str, multicast_ip: ip_address, base_vxlan_id: int = 42,
                 host_device_mapper=None,
                 default_host_device: str = "eth0"):
        self.network = network
        self.network_address_generator = BasicNetworkAddressGenerator(network, 0x815)
        if host_device_mapper is None:
            host_device_mapper = {}
        self.topo = None
        self.multicast_ip = multicast_ip
        self.base_vxlan_id = base_vxlan_id
        self.host_device_mapper = host_device_mapper
        self.default_host_device = default_host_device
        self.link_vxlanid: list[int] = []

    def set_host_device_name(self, node: 'Node', device: str):
        if not device:
            if node.name in self.host_device_mapper:
                del self.host_device_mapper[node.name]
        else:
            self.host_device_mapper[node.name] = device

    def configure(self):
        # Determine vxlan ids
        vxlan_id = self.base_vxlan_id
        for link in self.topo.links:
            if link.service1.executor != link.service2.executor:
                # It's a cross-executor link -> reserve vxlan id
                self.link_vxlanid.append(vxlan_id)
                vxlan_id += 1
            else:
                # Not a cross-execurot link -> no vxlan used here
                self.link_vxlanid.append(-1)

    def generate(self, node: Node, config: Configuration):
        if node.type is not NodeType.LINUX_DEBIAN and node.type is not NodeType.LINUX_ARCH:
            raise Exception("VxLan currently only supports configuring LinuxNodes")
        host_device = self.host_device_mapper[node.name] if node.name in self.host_device_mapper \
            else self.default_host_device

        br_num = 0
        link_index = -1

        # Iterate over links
        for link in self.topo.links:
            link_index += 1
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
                    # Add qdisc (if required)
                    if link.delay > 0 or link.loss > 0:
                        NetworkUtils.add_qdisc(config, link.intf1.bind_name, link.delay, link.loss,
                                               link.delay_variation, link.delay_correlation, link.loss_correlation)
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
                    config.add_command(
                        Command(f"ip link add vx-{intf.bind_name} type vxlan id {self.link_vxlanid[link_index]} "
                                f"group {self.multicast_ip} dev {host_device}"),
                        Command(f"ip link del vx-{intf.bind_name}"))
                    # Add vxlan device to our bridge
                    config.add_command(Command(f"brctl addif {intf.bind_name} vx-{intf.bind_name}"),
                                       Command(f"brctl delif {intf.bind_name} vx-{intf.bind_name}"))
                    # Set all devices up
                    NetworkUtils.set_up(config, intf.bind_name)
                    NetworkUtils.set_up(config, "vx-" + intf.bind_name)
                    # Add qdisc (if required, only on node of service1)
                    if link.service1.executor == node and (link.delay > 0 or link.loss > 0):
                        NetworkUtils.add_qdisc(config, "vx-" + link.intf1.bind_name, link.delay, link.loss,
                                               link.delay_variation, link.delay_correlation, link.loss_correlation)
                    # Routing in bridge is not required, as ports should enter "forwarding" state
                    # Can be seen with "brctl showstp <bridge>"

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(VxLanNetworkImplementation, self).to_dict(), **{
            'network': str(self.network),
            'multicast_ip': str(self.multicast_ip),
            'base_vxlan_id': self.base_vxlan_id,
            'host_device_mapper': self.host_device_mapper,
            'default_host_device': self.default_host_device,
            'link_vxlanid': [str(x) for x in self.link_vxlanid]
        }}

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'VxLanNetworkImplementation':
        """Internal method to initialize from dictionary."""
        ret = VxLanNetworkImplementation(ip_network(in_dict['network']),
                                         ip_address(in_dict['multicast_ip']),
                                         int(in_dict['base_vxlan_id']), in_dict['host_device_mapper'],
                                         in_dict['default_host_device'])
        x = in_dict['network_address_generator']
        ret.network_address_generator = ClassUtil.get_class_from_dict(x).from_dict(x)
        ret.link_vxlanid = [int(x) for x in in_dict['link_vxlanid']]
        return ret
