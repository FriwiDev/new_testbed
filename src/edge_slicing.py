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
        controller1 = RyuController(name="controller1", executor=node, script_path="../examples/defaults/simple_switch.py")
        switch1 = OVSSwitch(name="switch1", executor=node, fail_mode='secure', controllers=[controller1])
        switch2 = OVSSwitch(name="switch2", executor=node, fail_mode='secure', controllers=[controller1])
        switch3 = OVSSwitch(name="switch3", executor=node, fail_mode='secure', controllers=[controller1])
        switch4 = OVSSwitch(name="switch4", executor=node, fail_mode='secure', controllers=[controller1])
        switch5 = OVSSwitch(name="switch5", executor=node, fail_mode='secure', controllers=[controller1])
        switch6 = OVSSwitch(name="switch6", executor=node, fail_mode='secure', controllers=[controller1])
        switch7 = OVSSwitch(name="switch7", executor=node, fail_mode='secure', controllers=[controller1])
        switch8 = OVSSwitch(name="switch8", executor=node, fail_mode='secure', controllers=[controller1])
        switch9 = OVSSwitch(name="switch9", executor=node, fail_mode='secure', controllers=[controller1])
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        host3 = SimpleLXCHost(name="host3", executor=node)
        host4 = SimpleLXCHost(name="host4", executor=node)
        host5 = SimpleLXCHost(name="host5", executor=node)
        host6 = SimpleLXCHost(name="host6", executor=node)
        host7 = SimpleLXCHost(name="host7", executor=node)
        host8 = SimpleLXCHost(name="host8", executor=node)
        host9 = SimpleLXCHost(name="host9", executor=node)
        host10 = SimpleLXCHost(name="host10", executor=node)
        host11 = SimpleLXCHost(name="host11", executor=node)
        self.add_service(controller1)
        self.add_service(switch1)
        self.add_service(switch2)
        self.add_service(switch3)
        self.add_service(switch4)
        self.add_service(switch5)
        self.add_service(switch6)
        self.add_service(switch7)
        self.add_service(switch8)
        self.add_service(switch9)
        self.add_service(host1)
        self.add_service(host2)
        self.add_service(host3)
        self.add_service(host4)
        self.add_service(host5)
        self.add_service(host6)
        self.add_service(host7)
        self.add_service(host8)
        self.add_service(host9)
        self.add_service(host10)
        self.add_service(host11)
        # Create links
        # switches <-> controllers
        linkc1 = Link(self, service1=switch1, service2=controller1, link_type=LinkType.VXLAN)
        linkc2 = Link(self, service1=switch2, service2=controller1, link_type=LinkType.VXLAN)
        linkc3 = Link(self, service1=switch3, service2=controller1, link_type=LinkType.VXLAN)
        linkc4 = Link(self, service1=switch4, service2=controller1, link_type=LinkType.VXLAN)
        linkc5 = Link(self, service1=switch5, service2=controller1, link_type=LinkType.VXLAN)
        linkc6 = Link(self, service1=switch6, service2=controller1, link_type=LinkType.VXLAN)
        linkc7 = Link(self, service1=switch7, service2=controller1, link_type=LinkType.VXLAN)
        linkc8 = Link(self, service1=switch8, service2=controller1, link_type=LinkType.VXLAN)
        linkc9 = Link(self, service1=switch9, service2=controller1, link_type=LinkType.VXLAN)
        # switches <-> switches
        links12 = Link(self, service1=switch1, service2=switch2, link_type=LinkType.VXLAN)
        links23 = Link(self, service1=switch2, service2=switch3, link_type=LinkType.VXLAN)
        links34 = Link(self, service1=switch3, service2=switch4, link_type=LinkType.VXLAN)
        links45 = Link(self, service1=switch4, service2=switch5, link_type=LinkType.VXLAN)
        links56 = Link(self, service1=switch5, service2=switch6, link_type=LinkType.VXLAN)
        links67 = Link(self, service1=switch6, service2=switch7, link_type=LinkType.VXLAN)
        links78 = Link(self, service1=switch7, service2=switch8, link_type=LinkType.VXLAN)
        links89 = Link(self, service1=switch8, service2=switch9, link_type=LinkType.VXLAN)
        # switches <-> hosts
        linkh1s1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.VXLAN)
        linkh2s1 = Link(self, service1=host2, service2=switch1, link_type=LinkType.VXLAN)
        linkh3s1 = Link(self, service1=host3, service2=switch1, link_type=LinkType.VXLAN)

        linkh10s3 = Link(self, service1=host10, service2=switch3, link_type=LinkType.VXLAN)
        linkh11s3 = Link(self, service1=host11, service2=switch3, link_type=LinkType.VXLAN)

        linkh7s4 = Link(self, service1=host7, service2=switch4, link_type=LinkType.VXLAN)
        linkh7s5 = Link(self, service1=host7, service2=switch5, link_type=LinkType.VXLAN)
        linkh7s6 = Link(self, service1=host7, service2=switch6, link_type=LinkType.VXLAN)

        linkh8s7 = Link(self, service1=host8, service2=switch7, link_type=LinkType.VXLAN)
        linkh9s7 = Link(self, service1=host9, service2=switch7, link_type=LinkType.VXLAN)

        linkh4s9 = Link(self, service1=host4, service2=switch9, link_type=LinkType.VXLAN)
        linkh5s9 = Link(self, service1=host5, service2=switch9, link_type=LinkType.VXLAN)
        linkh6s9 = Link(self, service1=host6, service2=switch9, link_type=LinkType.VXLAN)

        # Add all links
        self.add_link(linkc1)
        self.add_link(linkc2)
        self.add_link(linkc3)
        self.add_link(linkc4)
        self.add_link(linkc5)
        self.add_link(linkc6)
        self.add_link(linkc7)
        self.add_link(linkc8)
        self.add_link(linkc9)

        self.add_link(links12)
        self.add_link(links23)
        self.add_link(links34)
        self.add_link(links45)
        self.add_link(links56)
        self.add_link(links67)
        self.add_link(links78)
        self.add_link(links89)

        self.add_link(linkh1s1)
        self.add_link(linkh2s1)
        self.add_link(linkh3s1)

        self.add_link(linkh10s3)
        self.add_link(linkh11s3)

        self.add_link(linkh7s4)
        self.add_link(linkh7s5)
        self.add_link(linkh7s6)

        self.add_link(linkh8s7)
        self.add_link(linkh9s7)

        self.add_link(linkh4s9)
        self.add_link(linkh5s9)
        self.add_link(linkh6s9)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, EdgeSlicing)


if __name__ == '__main__':
    main(sys.argv)
