from config.export.file_exporter import FileConfigurationExporter
from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from src.network.vxlan_network import VxLanNetworkImplementation
from topo.controller import RyuController
from topo.link import Link
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo


class TestTopo(Topo):

    def __init__(self, *args, **params):
        super().__init__(network_implementation=VxLanNetworkImplementation("10.0.0.0/24", "239.1.1.1",
                                                                           default_host_device="wlp2s0"),
                         *args, **params)

    def create(self, *args, **params):
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN)
        self.add_node(node)
        ryu = RyuController(name="controller1", executor=node)
        switch = OVSSwitch(name="switch1", executor=node, controllers=[ryu])
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(ryu)
        self.add_service(switch)
        self.add_service(host1)
        self.add_service(host2)
        self.add_link(Link(self, service1=ryu, service2=switch, delay=100, loss=0.25,
                           delay_variation=30, delay_correlation=0.35, loss_correlation=0.35))
        self.add_link(Link(self, service1=host1, service2=switch))
        self.add_link(Link(self, service1=host2, service2=switch))
        pass


def main():
    topo = TestTopo()
    # Serialize
    print(topo.export_topo())
    # Serialize and deserialize
    print(Topo.import_topo(topo.export_topo()).export_topo())
    # Export to file
    for name in topo.nodes:
        node = topo.nodes[name]
        config = node.get_configuration_builder(topo).build()
        exporter = FileConfigurationExporter(config, node, "export")
        exporter.export()


if __name__ == '__main__':
    main()
