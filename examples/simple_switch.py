import sys

from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo, TopoUtil


# Simple topology with one switch connecting two hosts.
class SimpleSwitch(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)
        # Create and append all services (one switch and two hosts)
        switch1 = OVSSwitch(name="switch1", executor=node, fail_mode='standalone')
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(switch1)
        self.add_service(host1)
        self.add_service(host2)
        # Create links between (host1, host2) <-> switch1
        link1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.VXLAN)
        link2 = Link(self, service1=switch1, service2=host2, link_type=LinkType.VXLAN)
        self.add_link(link1)
        self.add_link(link2)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, SimpleSwitch)


if __name__ == '__main__':
    main(sys.argv)
