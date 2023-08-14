import sys

from edgeslicing.components import EdgeslicingController, ESMF, DSMF, VPNGateway, QueueableOVSSwitch, Network, \
    NetworkBorderConfiguration, DeviceType, Utils, EdgeslicingLXCHost, Range
from platforms.linux_server.linux_node import LinuxNode
from topo.interface import Interface
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.topo import Topo, TopoUtil


class LocalEdgeslicing(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node1 = LinuxNode(name="node1", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@192.168.0.61")
        node1.add_interface(
            Interface(name="enp1s0", mac_address="68:05:ca:69:4f:1b").add_ip("10.10.10.1", "10.10.10.0/24"))
        nodebn = LinuxNode(name="nodebn", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@192.168.0.62")
        nodebn.add_interface(
            Interface(name="enp1s0", mac_address="68:05:ca:66:69:97").add_ip("10.10.10.2", "10.10.10.0/24"))
        node2 = LinuxNode(name="node2", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@192.168.0.63")
        node2.add_interface(
            Interface(name="enp1s0", mac_address="68:05:ca:66:6a:f8").add_ip("10.10.10.3", "10.10.10.0/24"))
        self.add_node(node1)
        self.add_node(nodebn)
        self.add_node(node2)

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
        vpn1 = VPNGateway(name="vpn1", executor=node1, network="net1")
        vpn2 = VPNGateway(name="vpn2", executor=node2, network="net2")
        controller1 = EdgeslicingController(name="controller1", executor=node1, network="net1")
        switch1a = QueueableOVSSwitch(name="switch1a", executor=node1, fail_mode='secure', dpid='1', controllers=[controller1], network="net1")
        switch1b = QueueableOVSSwitch(name="switch1b", executor=node1, fail_mode='secure', dpid='2', controllers=[controller1],
                                     network="net1")
        controller2 = EdgeslicingController(name="controller2", executor=node2, network="net2")
        switch2a = QueueableOVSSwitch(name="switch2a", executor=node2, fail_mode='secure', dpid='3', controllers=[controller2],
                                     network="net2")
        switch2b = QueueableOVSSwitch(name="switch2b", executor=node2, fail_mode='secure', dpid='4', controllers=[controller2], network="net2")
        controllerbn = EdgeslicingController(name="controllerbn", executor=nodebn, network="bn")
        switchbna = QueueableOVSSwitch(name="switchbna", executor=nodebn, fail_mode='secure', dpid="5", controllers=[controllerbn], network="bn")
        switchbnb = QueueableOVSSwitch(name="switchbnb", executor=nodebn, fail_mode='secure', dpid="6",
                                      controllers=[controllerbn], network="bn")
        host1 = EdgeslicingLXCHost(name="h1", executor=node1, network="net1")
        host2 = EdgeslicingLXCHost(name="h2", executor=node2, network="net2")
        adv1 = EdgeslicingLXCHost(name="adv1", executor=node1, network="net1", cpu="1")
        adv2 = EdgeslicingLXCHost(name="adv2", executor=node2, network="net2", cpu="1")

        # Append services
        self.add_service(controller1)
        self.add_service(switch1a)
        self.add_service(switch1b)
        self.add_service(controller2)
        self.add_service(switch2a)
        self.add_service(switch2b)
        self.add_service(controllerbn)
        self.add_service(switchbna)
        self.add_service(switchbnb)
        self.add_service(vpn1)
        self.add_service(vpn2)
        self.add_service(host1)
        self.add_service(host2)
        self.add_service(adv1)
        self.add_service(adv2)

        # Create links
        link1 = Link(self, service1=host1, service2=switch1a, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link2 = Link(self, service1=switch1a, service2=switch1b, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link3 = Link(self, service1=switch1b, service2=vpn1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link4 = Link(self, service1=vpn1, service2=switchbna, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link5 = Link(self, service1=switchbna, service2=switchbnb, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link6 = Link(self, service1=switchbnb, service2=vpn2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link7 = Link(self, service1=vpn2, service2=switch2a, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link8 = Link(self, service1=switch2a, service2=switch2b, link_type=LinkType.VXLAN, bandwidth=1000000000)
        link9 = Link(self, service1=switch2b, service2=host2, link_type=LinkType.VXLAN, bandwidth=1000000000)

        # Adversaries get more bandwidth to be able to disturb - just like in our base example
        linka1 = Link(self, service1=adv1, service2=switch1a, link_type=LinkType.VXLAN, bandwidth=10000000000)  # 10G
        linka2 = Link(self, service1=adv2, service2=switch2b, link_type=LinkType.VXLAN, bandwidth=10000000000)  # 10G

        # VPN bypass links for normal traffic
        linkb1 = Link(self, service1=switch1b, service2=switchbna, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkb2 = Link(self, service1=switch2a, service2=switchbnb, link_type=LinkType.VXLAN, bandwidth=1000000000)

        # Append all links
        self.add_link(link1)
        self.add_link(link2)
        self.add_link(link3)
        self.add_link(link4)
        self.add_link(link5)
        self.add_link(link6)
        self.add_link(link7)
        self.add_link(link8)
        self.add_link(link9)

        self.add_link(linka1)
        self.add_link(linka2)

        self.add_link(linkb1)
        self.add_link(linkb2)

        # Create network borders
        network_borders_net1 = [
            NetworkBorderConfiguration(network_name="bn", device_name="vpn1", device_type=DeviceType.VPN,
                                       connection=Utils.get_connection(vpn1, "bn"))
        ]

        network_borders_net2 = [
            NetworkBorderConfiguration(network_name="bn", device_name="vpn2", device_type=DeviceType.VPN,
                                       connection=Utils.get_connection(vpn2, "bn"))
        ]

        network_borders_bn = [
            NetworkBorderConfiguration(network_name="net1", device_name="switchbna", device_type=DeviceType.SWITCH,
                                       connection=Utils.get_connection(switchbna, "net1")),
            NetworkBorderConfiguration(network_name="net2", device_name="switchbnb", device_type=DeviceType.SWITCH,
                                       connection=Utils.get_connection(switchbnb, "net2"))
        ]

        # Create control structures
        dsmf1 = DSMF(name="DSMF1", executor=node1, network="net1", controllers=[controller1], vpn_gateways=[vpn1, vpn2], networks=networks, switches=[switch1a, switch1b], network_borders=network_borders_net1)
        esmf1 = ESMF(name="ESMF1", executor=node1, network="net1", coordinators=[], vpn_gateways=[vpn1, vpn2], networks=networks, domain_controller=dsmf1, slice_id_range=Range(1000, 1999), tunnel_id_range=Range(1000, 1999))
        dsmf2 = DSMF(name="DSMF2", executor=node2, network="net2", controllers=[controller2], vpn_gateways=[vpn1, vpn2], networks=networks, switches=[switch2a, switch2b], network_borders=network_borders_net2)
        esmf2 = ESMF(name="ESMF2", executor=node2, network="net2", coordinators=[], vpn_gateways=[vpn1, vpn2], networks=networks, domain_controller=dsmf2, slice_id_range=Range(2000, 2999), tunnel_id_range=Range(2000, 2999))
        dtmf = DSMF(name="DTMF", executor=node1, network="bn", controllers=[controllerbn], vpn_gateways=[vpn1, vpn2],
                     networks=networks, switches=[switchbna, switchbnb], network_borders=network_borders_bn)
        ctmf = ESMF(name="CTMF", executor=node1, network="bn", coordinators=[], vpn_gateways=[vpn1, vpn2],
                     networks=networks, domain_controller=dtmf, slice_id_range=Range(3000, 3999),
                     tunnel_id_range=Range(3000, 3999))
        esmf1.coordinators.append(esmf2)
        esmf2.coordinators.append(esmf1)
        esmf1.coordinators.append(ctmf)
        esmf2.coordinators.append(ctmf)

        # Append services
        self.add_service(esmf1)
        self.add_service(dsmf1)
        self.add_service(esmf2)
        self.add_service(dsmf2)
        self.add_service(ctmf)
        self.add_service(dtmf)

        # Create links
        linke1 = Link(self, service1=host1, service2=esmf1, link_type=LinkType.VXLAN, bandwidth=1000000000)

        linkc10 = Link(self, service1=esmf1, service2=esmf2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc11a = Link(self, service1=switch1a, service2=dsmf1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc11b = Link(self, service1=switch1b, service2=dsmf1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc12 = Link(self, service1=vpn1, service2=dsmf1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc13 = Link(self, service1=dsmf1, service2=esmf1, link_type=LinkType.VXLAN, bandwidth=1000000000)

        linkc21a = Link(self, service1=switch2a, service2=dsmf2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc21b = Link(self, service1=switch2b, service2=dsmf2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc22 = Link(self, service1=vpn2, service2=dsmf2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc23 = Link(self, service1=dsmf2, service2=esmf2, link_type=LinkType.VXLAN, bandwidth=1000000000)

        linkc30 = Link(self, service1=dsmf1, service2=controller1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc31a = Link(self, service1=switch1a, service2=controller1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc31b = Link(self, service1=switch1b, service2=controller1, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc32 = Link(self, service1=dsmf2, service2=controller2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc33a = Link(self, service1=switch2a, service2=controller2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc33b = Link(self, service1=switch2b, service2=controller2, link_type=LinkType.VXLAN, bandwidth=1000000000)

        linkc40 = Link(self, service1=esmf1, service2=ctmf, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc41 = Link(self, service1=ctmf, service2=esmf2, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc42 = Link(self, service1=ctmf, service2=dtmf, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc43a = Link(self, service1=dtmf, service2=switchbna, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc43b = Link(self, service1=dtmf, service2=switchbnb, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc44 = Link(self, service1=dtmf, service2=controllerbn, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc45a = Link(self, service1=switchbna, service2=controllerbn, link_type=LinkType.VXLAN, bandwidth=1000000000)
        linkc45b = Link(self, service1=switchbnb, service2=controllerbn, link_type=LinkType.VXLAN, bandwidth=1000000000)

        linkc50 = Link(self, service1=adv1, service2=esmf1, link_type=LinkType.VXLAN, bandwidth=1000000000)

        # Append all links
        self.add_link(linke1)

        self.add_link(linkc10)
        self.add_link(linkc11a)
        self.add_link(linkc11b)
        self.add_link(linkc12)
        self.add_link(linkc13)

        self.add_link(linkc21a)
        self.add_link(linkc21b)
        self.add_link(linkc22)
        self.add_link(linkc23)

        self.add_link(linkc30)
        self.add_link(linkc31a)
        self.add_link(linkc31b)
        self.add_link(linkc32)
        self.add_link(linkc33a)
        self.add_link(linkc33b)

        self.add_link(linkc40)
        self.add_link(linkc41)
        self.add_link(linkc42)
        self.add_link(linkc43a)
        self.add_link(linkc43b)
        self.add_link(linkc44)
        self.add_link(linkc45a)
        self.add_link(linkc45b)

        self.add_link(linkc50)

        # We always use the same port to communicate with other servers
        for li in self.links:
            self.network_implementation.set_link_interface_mapping(li, "enp1s0", "enp1s0")
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, LocalEdgeslicing)


if __name__ == '__main__':
    main(sys.argv)
