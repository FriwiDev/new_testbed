from ipaddress import ip_network

from config.configuration import Configuration, Command
from network.network_address_generator import BasicNetworkAddressGenerator
from network.network_implementation import NetworkImplementation
from network.network_utils import NetworkUtils
from topo.node import Node, NodeType
from topo.util import ClassUtil


class DirectNetworkImplementation(NetworkImplementation):
    def __init__(self, internal_network: ip_network or str):
        self.network = internal_network
        self.network_address_generator = BasicNetworkAddressGenerator(internal_network, 0x815)

    def set_link_interface_mapping(self, link: 'Link', dev_name1: str, dev_name2: str):
        # Check collissions
        if dev_name1 and self.has_link(link.service1.executor, dev_name1):
            raise Exception(f"Already got another link with node {link.service1.executor.name} and device {dev_name1} "
                            f"(needs to be unique)")
        if dev_name2 and self.has_link(link.service2.executor, dev_name2):
            raise Exception(f"Already got another link with node {link.service2.executor.name} and device {dev_name2} "
                            f"(needs to be unique)")
        if (dev_name1 and not dev_name2) or (dev_name2 and not dev_name1):
            raise Exception(f"Device names can either be both None or both set")
        link.intf1.bind_name = dev_name1
        link.intf2.bind_name = dev_name2
        # Replace interfaces, if info is set
        if dev_name1:
            link.intf_name1 = dev_name1
            link.service1.remove_interface(link.intf1.name)
            link.intf1 = link.service1.executor.get_interface(dev_name1)
            link.service1.add_interface(link.intf1)
            link.intf1.bind_name = dev_name1
        if dev_name2:
            link.intf_name2 = dev_name2
            link.service2.remove_interface(link.intf2.name)
            link.intf2 = link.service2.executor.get_interface(dev_name2)
            link.service2.add_interface(link.intf2)
            link.intf2.bind_name = dev_name2

    def has_link(self, node: 'Node', dev_name: str) -> bool:
        for link in self.topo.links:
            if link.service1.executor == node and link.intf1 and link.intf1.bind_name == dev_name:
                return True
            if link.service2.executor == node and link.intf2 and link.intf2.bind_name == dev_name:
                return True
        return False

    def configure(self):
        # Check that all links got provided a bind name
        for link in self.topo.links:
            if link.service1.executor != link.service2.executor:
                if not link.intf1 or not link.intf2 or not link.intf1.bind_name or not link.intf2.bind_name:
                    raise Exception(f"Link {link.service1.name} <-> {link.service2.name} misses binding information. "
                                    f"Please set using <DirectNetworkImplementation>.set_link_interface_mapping(...)")

    def generate(self, node: Node, config: Configuration):
        if node.type is not NodeType.LINUX_DEBIAN and node.type is not NodeType.LINUX_ARCH:
            raise Exception("DirectNetwork currently only supports configuring LinuxNodes")

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
                    # We only manage one end
                    intf = link.intf1 if link.service1.executor == node else link.intf2
                    # Set all devices up
                    NetworkUtils.set_up(config, intf.bind_name)
                    # Add qdisc (if required, only on node of service1)
                    if link.service1.executor == node and (link.delay > 0 or link.loss > 0):
                        NetworkUtils.add_qdisc(config, link.intf1.bind_name, link.delay, link.loss,
                                               link.delay_variation, link.delay_correlation, link.loss_correlation)
                    # Routing in bridge is not required, as ports should enter "forwarding" state
                    # Can be seen with "brctl showstp <bridge>"

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(DirectNetworkImplementation, self).to_dict(), **{
            'network': str(self.network)
        }}

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'DirectNetworkImplementation':
        """Internal method to initialize from dictionary."""
        ret = DirectNetworkImplementation(ip_network(in_dict['network']))
        x = in_dict['network_address_generator']
        ret.network_address_generator = ClassUtil.get_class_from_dict(x).from_dict(x)
        return ret
