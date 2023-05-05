import sys

from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.controller import RyuController
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo, TopoUtil


class EdgeSlicing(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)
        # Create and append all services
        controller1 = RyuController(name="controller1", executor=node, script_path="../examples/defaults/edgeslicing_ryu.py")
        switch1 = OVSSwitch(name="switch1", executor=node, fail_mode='secure', controllers=[controller1])
        switch2 = OVSSwitch(name="switch2", executor=node, fail_mode='secure', controllers=[controller1])
        switch3 = OVSSwitch(name="switch3", executor=node, fail_mode='secure', controllers=[controller1])
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(controller1)
        self.add_service(switch1)
        self.add_service(switch2)
        self.add_service(switch3)
        self.add_service(host1)
        self.add_service(host2)
        # Create links
        # switches <-> controllers
        linkc1 = Link(self, service1=switch1, service2=controller1, link_type=LinkType.VXLAN)
        linkc2 = Link(self, service1=switch2, service2=controller1, link_type=LinkType.VXLAN)
        linkc3 = Link(self, service1=switch3, service2=controller1, link_type=LinkType.VXLAN)
        # switches <-> switches
        links12 = Link(self, service1=switch1, service2=switch2, link_type=LinkType.VXLAN)
        links23 = Link(self, service1=switch2, service2=switch3, link_type=LinkType.VXLAN)
        # switches <-> hosts
        linkh1s1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.VXLAN)
        links3h2 = Link(self, service1=switch3, service2=host2, link_type=LinkType.VXLAN)

        # Add all links
        self.add_link(linkc1)
        self.add_link(linkc2)
        self.add_link(linkc3)

        self.add_link(links12)
        self.add_link(links23)

        self.add_link(linkh1s1)
        self.add_link(links3h2)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, EdgeSlicing)


if __name__ == '__main__':
    main(sys.argv)
