import sys

from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.interface import Interface
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.topo import Topo, TopoUtil


# Simple topology with two hosts talking from two separate nodes.
# You will need to fill in information about your two nodes below.
class SimpleCrossNode(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create nodes to execute on
        node1 = LinuxNode(name="testnode1", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@10.0.1.1")
        node1.add_interface(Interface("enp3s0").add_ip("10.0.1.1", "10.0.1.0/24"))
        self.add_node(node1)
        node2 = LinuxNode(name="testnode2", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@10.0.1.2")
        node2.add_interface(Interface("enp3s1").add_ip("10.0.1.2", "10.0.1.0/24"))
        self.add_node(node2)
        # Create and append all services (two hosts)
        host1 = SimpleLXCHost(name="host1", executor=node1)
        host2 = SimpleLXCHost(name="host2", executor=node2)
        self.add_service(host1)
        self.add_service(host2)

        # Create link between host1 <-> host2 with type VXLAN (talk via the specified devices with VXLAN)
        link = Link(self, service1=host1, service2=host2, link_type=LinkType.VXLAN)
        # Direct link bindings (without vxlan) are also be possible like this:
        # > link = Link(self, service1=host1, service2=host2, link_type=LinkType.DIRECT)

        # Add link (before setting mappings below)
        self.add_link(link)
        # Only for links between nodes: Specify which node interfaces to use on node1 (enp3s0) and on node2 (enp3s1)
        self.network_implementation.set_link_interface_mapping(link, "enp3s0", "enp3s1")
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, SimpleCrossNode)


if __name__ == '__main__':
    main(sys.argv)
