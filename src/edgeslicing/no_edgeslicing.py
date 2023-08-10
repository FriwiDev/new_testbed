import sys

from edgeslicing.components import EdgeslicingLXCHost
from platforms.linux_server.linux_node import LinuxNode
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo, TopoUtil

"""
A baseline scenario to test what happens when we do not use our edgeslicing approach.
We build a setup with two switches so that we have a shared domain between them to test on.
All links are limited to 1G, except for those of the adversaries.
"""
class NoEdgeslicing(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)
        # Create and append all services (one switch and two hosts)
        switch1 = OVSSwitch(name="switch1", executor=node, fail_mode='standalone')
        switch2 = OVSSwitch(name="switch2", executor=node, fail_mode='standalone')
        host1 = EdgeslicingLXCHost(name="host1", executor=node, network="net1")
        host2 = EdgeslicingLXCHost(name="host2", executor=node, network="net2")
        adv1 = EdgeslicingLXCHost(name="adv1", executor=node, network="net1")
        adv2 = EdgeslicingLXCHost(name="adv2", executor=node, network="net2")
        self.add_service(switch1)
        self.add_service(switch2)
        self.add_service(host1)
        self.add_service(host2)
        self.add_service(adv1)
        self.add_service(adv2)
        # Create links
        link1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link2 = Link(self, service1=adv1, service2=switch1, link_type=LinkType.VXLAN, bandwidth=2000000000)
        link3 = Link(self, service1=switch1, service2=switch2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link4 = Link(self, service1=switch2, service2=host2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link5 = Link(self, service1=switch2, service2=adv2, link_type=LinkType.VXLAN, bandwidth=2000000000)
        self.add_link(link1)
        self.add_link(link2)
        self.add_link(link3)
        self.add_link(link4)
        self.add_link(link5)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, NoEdgeslicing)


if __name__ == '__main__':
    main(sys.argv)
