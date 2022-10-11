from ipaddress import ip_address, ip_network

from config.configuration import Configuration, Command
from network.network_address_generator import BasicNetworkAddressGenerator
from network.network_implementation import NetworkImplementation
from network.network_utils import NetworkUtils
from topo.link import LinkType, Link
from topo.node import Node, NodeType
from topo.util import ClassUtil


class DefaultNetworkImplementation(NetworkImplementation):
    def __init__(self, network: ip_network or str, multicast_ip: ip_address, base_vxlan_id: int = 42):
        self.network = network
        self.network_address_generator = BasicNetworkAddressGenerator(network, 0x815)
        self.topo = None
        self.multicast_ip = multicast_ip
        self.base_vxlan_id = base_vxlan_id
        self.link_id_reference = 0
        self.link_vxlanid: dict[str, int] = {}
        self.link_vxlan_mapping: dict[str, list[str]] = {}

    def set_link_interface_mapping(self, link: 'Link', dev_name1: str, dev_name2: str):
        if not link in self.topo.links:
            raise Exception(f"You need to add link {link.service1.name} <-> {link.service2.name} to the topology first"
                            f" before setting interface mappings")
        if not link.service1.executor.get_interface(dev_name1):
            raise Exception(f"Bind device {dev_name1} for link {link.service1.name} <-> {link.service2.name} does not "
                            f"exist on {link.service1.executor.name}")
        if not link.service2.executor.get_interface(dev_name2):
            raise Exception(f"Bind device {dev_name2} for link {link.service1.name} <-> {link.service2.name} does not "
                            f"exist on {link.service2.executor.name}")
        if link.link_id == -1:
            link.link_id = self.link_id_reference
            self.link_id_reference += 1
        # Check collissions
        if dev_name1 and self.has_link(link.service1.executor, dev_name1):
            raise Exception(
                f"Already got another link with node {link.service1.executor.name} and device {dev_name1} "
                f"(needs to be unique)")
        if dev_name2 and self.has_link(link.service2.executor, dev_name2):
            raise Exception(
                f"Already got another link with node {link.service2.executor.name} and device {dev_name2} "
                f"(needs to be unique)")
        if link.link_type == LinkType.DIRECT:
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
        elif link.link_type == LinkType.VXLAN:
            self.link_vxlan_mapping[str(link.link_id)] = [dev_name1, dev_name2]
        else:
            raise Exception(f"Unknown/unsupported link type for link {link.service1.name} <-> {link.service2.name}")

    def has_link(self, node: 'Node', dev_name: str) -> bool:
        for link in self.topo.links:
            if link.service1.executor == node and link.intf1 and link.intf1.bind_name == dev_name:
                return True
            if link.service2.executor == node and link.intf2 and link.intf2.bind_name == dev_name:
                return True
            if link.link_id in self.link_vxlan_mapping:
                if dev_name in self.link_vxlan_mapping[link.link_id]:
                    return True
        return False

    def configure(self):
        # Check that all links got provided a bind name
        for link in self.topo.links:
            if link.link_type == LinkType.DIRECT:
                if link.service1.executor != link.service2.executor:
                    if not link.intf1 or not link.intf2 or not link.intf1.bind_name or not link.intf2.bind_name:
                        raise Exception(
                            f"Direct link {link.service1.name} <-> {link.service2.name} misses binding information. "
                            f"Please set using <DefaultNetworkImplementation>.set_link_interface_mapping(...)")
            elif link.link_type == LinkType.VXLAN:
                if link.service1.executor != link.service2.executor:
                    if not link.intf1 or not link.intf2 or str(link.link_id) not in self.link_vxlan_mapping:
                        raise Exception(
                            f"Vxlan link {link.service1.name} <-> {link.service2.name} misses binding information. "
                            f"Please set using <DefaultNetworkImplementation>.set_link_interface_mapping(...)")
        # Determine vxlan ids
        vxlan_id = self.base_vxlan_id
        for link in self.topo.links:
            if link.link_id == -1:
                link.link_id = self.link_id_reference
                self.link_id_reference += 1
            if link.link_type == LinkType.VXLAN:
                if link.service1.executor != link.service2.executor:
                    # It's a cross-executor vxlan link -> reserve vxlan id
                    self.link_vxlanid[str(link.link_id)] = vxlan_id
                    vxlan_id += 1

    def generate(self, node: Node, config: Configuration):
        if node.type is not NodeType.LINUX_DEBIAN and node.type is not NodeType.LINUX_ARCH:
            raise Exception("DefaultNetworkImplementation currently only supports configuring LinuxNodes")

        # Iterate over links
        for link in self.topo.links:
            self.generate_link(node, config, link)

    def generate_link(self, node: Node, config: Configuration, link: Link):
        if link.service1.executor == node or link.service2.executor == node:
            # We participate
            if link.service1.executor == node and link.service2.executor == node:
                # We are the only participant -> route internally
                # Create two bridges on which the services can bind
                if link.intf1.bind_name is None:
                    link.intf1.bind_name = f"br{link.link_id}a"
                if link.intf2.bind_name is None:
                    link.intf2.bind_name = f"br{link.link_id}b"
                # Create veth link
                config.add_command(
                    Command(f"ip link add v{link.intf1.bind_name} type veth peer v{link.intf2.bind_name}"),
                    Command(f"ip link del v{link.intf1.bind_name}"))
                # Create two bridges
                config.add_command(
                    Command(f"brctl addbr {link.intf1.bind_name}"),
                    Command(f"ip link del {link.intf1.bind_name}")
                )
                config.add_command(
                    Command(f"brctl addbr {link.intf2.bind_name}"),
                    Command(f"ip link del {link.intf2.bind_name}")
                )
                # Add veth pairs to bridges
                config.add_command(Command(f"brctl addif {link.intf1.bind_name} v{link.intf1.bind_name}"),
                                   Command(f"brctl delif {link.intf1.bind_name} v{link.intf1.bind_name}"))
                config.add_command(Command(f"brctl addif {link.intf2.bind_name} v{link.intf2.bind_name}"),
                                   Command(f"brctl delif {link.intf2.bind_name} v{link.intf2.bind_name}"))
                # Set all devices up
                NetworkUtils.set_up(config, link.intf1.bind_name)
                NetworkUtils.set_up(config, link.intf2.bind_name)
                NetworkUtils.set_up(config, "v" + link.intf1.bind_name)
                NetworkUtils.set_up(config, "v" + link.intf2.bind_name)
                # Add qdisc (if required)
                if link.delay > 0 or link.loss > 0:
                    NetworkUtils.add_qdisc(config, "v" + link.intf1.bind_name, link.delay, link.loss,
                                           link.delay_variation, link.delay_correlation, link.loss_correlation)
            else:
                if link.link_type == LinkType.VXLAN:
                    # We only manage one end -> route via vxlan
                    intf = link.intf1 if link.service1.executor == node else link.intf2
                    if link.service1.executor == node:
                        host_device = self.link_vxlan_mapping[str(link.link_id)][0]
                    else:
                        host_device = self.link_vxlan_mapping[str(link.link_id)][1]
                    if intf.bind_name is None:
                        intf.bind_name = f"br{link.link_id}"
                    # Create one bridge on which the service can bind
                    config.add_command(Command(f"brctl addbr {intf.bind_name}"),
                                       Command(f"brctl delbr {intf.bind_name}"))
                    # Create vxlan device used for this service
                    config.add_command(
                        Command(f"ip link add vx-{intf.bind_name} type vxlan id {self.link_vxlanid[str(link.link_id)]} "
                                f"group {self.multicast_ip} dev {host_device}"),
                        Command(f"ip link del vx-{intf.bind_name}"))
                    # Add vxlan device to our bridge
                    config.add_command(Command(f"brctl addif {intf.bind_name} vx-{intf.bind_name}"),
                                       Command(f"brctl delif {intf.bind_name} vx-{intf.bind_name}"))
                    # Set all devices up
                    NetworkUtils.set_up(config, intf.bind_name)
                    NetworkUtils.set_up(config, "vx-" + intf.bind_name)
                    # Add qdisc (if required, only on node of service1)
                    self.generate_qdisc(node, config, link)
                    # Routing in bridge is not required, as ports should enter "forwarding" state
                    # Can be seen with "brctl showstp <bridge>"
                elif link.link_type == LinkType.DIRECT:
                    # We only manage one end
                    intf = link.intf1 if link.service1.executor == node else link.intf2
                    # Set all devices up
                    NetworkUtils.set_up(config, intf.bind_name)
                    # Add qdisc (if required, only on node of service1)
                    self.generate_qdisc(node, config, link)
                    # Routing in bridge is not required, as ports should enter "forwarding" state
                    # Can be seen with "brctl showstp <bridge>"
                else:
                    raise Exception("Unknown link type for link " + link.service1.name + " <-> " + link.service2.name)

    def generate_qdisc(self, node: Node, config: Configuration, link: Link):
        if link.service1.executor == node and (link.delay > 0 or link.loss > 0):
            NetworkUtils.add_qdisc(config, ("vx-" if link.link_type is LinkType.VXLAN else "") + link.intf1.bind_name,
                                   link.delay, link.loss,
                                   link.delay_variation, link.delay_correlation, link.loss_correlation)

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(DefaultNetworkImplementation, self).to_dict(), **{
            'network': str(self.network),
            'multicast_ip': str(self.multicast_ip),
            'base_vxlan_id': self.base_vxlan_id,
            'link_id_reference': self.link_id_reference,
            'link_vxlanid': self.link_vxlanid,
            'link_vxlan_mapping': self.link_vxlan_mapping
        }}

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'DefaultNetworkImplementation':
        """Internal method to initialize from dictionary."""
        ret = DefaultNetworkImplementation(ip_network(in_dict['network']),
                                           ip_address(in_dict['multicast_ip']),
                                           int(in_dict['base_vxlan_id']))
        x = in_dict['network_address_generator']
        ret.network_address_generator = ClassUtil.get_class_from_dict(x).from_dict(x)
        ret.link_id_reference = int(in_dict['link_id_reference'])
        ret.link_vxlanid = in_dict['link_vxlanid']
        ret.link_vxlan_mapping = in_dict['link_vxlan_mapping']
        return ret
