import sys
import typing

from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.controller import RyuController
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo, TopoUtil


# Simple topology with one switch connecting two hosts. The switch has a controller, which sets the switch
# up to act like a normal transparent switch.
class SimpleController(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)
        # Create and append all services (one controller, one switch and two hosts)
        controller1 = RyuController(name="controller1", executor=node, script_path="../examples/defaults/simple_switch.py")
        switch1 = OVSSwitch(name="switch1", executor=node, fail_mode='secure', controllers=[controller1])
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(controller1)
        self.add_service(switch1)
        self.add_service(host1)
        self.add_service(host2)
        # Create links between (host1, host2, controller1) <-> switch1
        linkc1 = Link(self, service1=switch1, service2=controller1, link_type=LinkType.VXLAN)
        link1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.VXLAN)
        link2 = Link(self, service1=switch1, service2=host2, link_type=LinkType.VXLAN)
        self.add_link(linkc1)
        self.add_link(link1)
        self.add_link(link2)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: typing.List[str]):
    TopoUtil.run_build(argv, SimpleController)


if __name__ == '__main__':
    main(sys.argv)
