import sys

from extensions.wireguard_extension_builder import WireguardExtensionBuilder
from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.topo import Topo, TopoUtil


# Simple topology with two hosts that are connected via wireguard.
class SimpleWireguard(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)
        # Create and append all services (two hosts)
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(host1)
        self.add_service(host2)
        # Create links between host1 <-> host2
        link = Link(self, service1=host1, service2=host2, link_type=LinkType.VXLAN)
        self.add_link(link)
        # Create wireguard tunnel
        # Explanation: connect host1 and host2, using their interfaces (can be obtained from the link)
        #              Use first ip for host1 and second ip for host2. Last parameter is virtual network address.
        WireguardExtensionBuilder(host1, host2, link.intf1, link.intf2,
                                  "192.168.178.1", "192.168.178.2", "192.168.178.0/24") \
            .build()
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: typing.List[str]):
    TopoUtil.run_build(argv, SimpleWireguard)


if __name__ == '__main__':
    main(sys.argv)
