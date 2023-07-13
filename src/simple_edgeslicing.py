import ipaddress
import sys

from config.configuration import Command
from edgeslicing.components import EdgeslicingController, ESMF, DSMF, VPNGateway, QueueableOVSSwitch, Network, \
    NetworkBorderConfiguration, DeviceType, Utils, EdgeslicingLXCHost, Range, DSMFType
from platforms.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.controller import RyuController
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo, TopoUtil


class SimpleEdgeslicing(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)

        # Create networks
        networks = [
            Network(name="net1", reachable=["bn"], preferred_vpn=["vpn1"],
                    subnets=[self.network_implementation.network]),
            Network(name="bn", reachable=["net1", "net2"], preferred_vpn=[],
                    subnets=[self.network_implementation.network]),
            Network(name="net2", reachable=["bn"], preferred_vpn=["vpn2"],
                    subnets=[self.network_implementation.network])
        ]

        # Create data plane + controllers
        vpn1 = VPNGateway(name="vpn1", executor=node, network="net1")
        vpn2 = VPNGateway(name="vpn2", executor=node, network="net2")
        controller1 = EdgeslicingController(name="controller1", executor=node, network="net1")
        switch1 = QueueableOVSSwitch(name="switch1", executor=node, fail_mode='secure', controllers=[controller1], network="net1")
        controller2 = EdgeslicingController(name="controller2", executor=node, network="net2")
        switch2 = QueueableOVSSwitch(name="switch2", executor=node, fail_mode='secure', controllers=[controller2], network="net2")
        switchbn = QueueableOVSSwitch(name="switchbn", executor=node, fail_mode='standalone', dpid="3", network="bn")
        host1 = EdgeslicingLXCHost(name="h1", executor=node, network="net1")
        host2 = EdgeslicingLXCHost(name="h2", executor=node, network="net2")

        # Append services
        self.add_service(controller1)
        self.add_service(switch1)
        self.add_service(controller2)
        self.add_service(switch2)
        self.add_service(switchbn)
        self.add_service(vpn1)
        self.add_service(vpn2)
        self.add_service(host1)
        self.add_service(host2)

        # Create links
        link1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.VXLAN)
        link2 = Link(self, service1=switch1, service2=vpn1, link_type=LinkType.VXLAN)
        link3 = Link(self, service1=vpn1, service2=switchbn, link_type=LinkType.VXLAN)
        link4 = Link(self, service1=switchbn, service2=vpn2, link_type=LinkType.VXLAN)
        link5 = Link(self, service1=vpn2, service2=switch2, link_type=LinkType.VXLAN)
        link6 = Link(self, service1=switch2, service2=host2, link_type=LinkType.VXLAN)

        # Append all links
        self.add_link(link1)
        self.add_link(link2)
        self.add_link(link3)
        self.add_link(link4)
        self.add_link(link5)
        self.add_link(link6)

        # Create network borders
        network_borders_net1 = [
            NetworkBorderConfiguration(network_name="bn", device_name="vpn1", device_type=DeviceType.VPN,
                                       connection=Utils.get_connections(vpn1))
        ]

        network_borders_net2 = [
            NetworkBorderConfiguration(network_name="bn", device_name="vpn2", device_type=DeviceType.VPN,
                                       connection=Utils.get_connections(vpn2))
        ]

        # Create controll structures
        dsmf1 = DSMF(name="DSMF1", executor=node, network="net1", controllers=[controller1], vpn_gateways=[vpn1, vpn2], networks=networks, switches=[switch1], network_borders=network_borders_net1)
        esmf1 = ESMF(name="ESMF1", executor=node, network="net1", coordinators=[], vpn_gateways=[vpn1, vpn2], networks=networks, domain_controller=dsmf1, slice_id_range=Range(1000, 1999), tunnel_id_range=Range(1000, 1999))
        dsmf2 = DSMF(name="DSMF2", executor=node, network="net2", controllers=[controller2], vpn_gateways=[vpn1, vpn2], networks=networks, switches=[switch2], network_borders=network_borders_net2)
        esmf2 = ESMF(name="ESMF2", executor=node, network="net2", coordinators=[], vpn_gateways=[vpn1, vpn2], networks=networks, domain_controller=dsmf2, slice_id_range=Range(2000, 2999), tunnel_id_range=Range(2000, 2999))
        esmf1.coordinators.append(esmf2)
        esmf2.coordinators.append(esmf1)

        # Append services
        self.add_service(esmf1)
        self.add_service(dsmf1)
        self.add_service(esmf2)
        self.add_service(dsmf2)

        # Create links
        linke1 = Link(self, service1=host1, service2=esmf1, link_type=LinkType.VXLAN)

        linkc10 = Link(self, service1=esmf1, service2=esmf2, link_type=LinkType.VXLAN)
        linkc11 = Link(self, service1=switch1, service2=dsmf1, link_type=LinkType.VXLAN)
        linkc12 = Link(self, service1=vpn1, service2=dsmf1, link_type=LinkType.VXLAN)
        linkc13 = Link(self, service1=dsmf1, service2=esmf1, link_type=LinkType.VXLAN)

        linkc21 = Link(self, service1=switch2, service2=dsmf2, link_type=LinkType.VXLAN)
        linkc22 = Link(self, service1=vpn2, service2=dsmf2, link_type=LinkType.VXLAN)
        linkc23 = Link(self, service1=dsmf2, service2=esmf2, link_type=LinkType.VXLAN)

        # Append all links
        self.add_link(linke1)

        self.add_link(linkc10)
        self.add_link(linkc11)
        self.add_link(linkc12)
        self.add_link(linkc13)

        self.add_link(linkc21)
        self.add_link(linkc22)
        self.add_link(linkc23)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, SimpleEdgeslicing)


if __name__ == '__main__':
    main(sys.argv)
