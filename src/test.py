import sys

from extensions.wireguard_extension_builder import WireguardExtensionBuilder
from network.direct_network import DirectNetworkImplementation
from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.interface import Interface
from topo.link import Link
from topo.node import NodeType
from topo.topo import Topo


class TestTopo(Topo):

    def __init__(self, *args, **params):
        super().__init__(network_implementation=DirectNetworkImplementation("10.0.0.0/24"),
                         *args, **params)

    def create(self, *args, **params):
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN)
        node.add_interface(Interface("wlp2s0").add_ip("10.0.1.28", "10.0.1.0/24")) \
            .add_interface(Interface("enp3s0").add_ip("10.0.1.4", "10.0.1.0/24"))
        self.add_node(node)
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(host1)
        self.add_service(host2)
        link = Link(self, service1=host1, service2=host2)
        self.add_link(link)
        WireguardExtensionBuilder(host1, host2, link.intf1, link.intf2,
                                  "192.168.178.1", "192.168.178.2", "192.168.178.0/24") \
            .build()
        pass


def main(argv: list[str]):
    topo = TestTopo()
    # Serialize to stdout
    print(topo.export_topo())
    # TODO remove
    # Serialize and deserialize
    # print(Topo.import_topo(topo.export_topo()).export_topo())
    # Export to file
    # for name in topo.nodes:
    #    node = topo.nodes[name]
    #    config = node.get_configuration_builder(topo).build()
    #    exporter = FileConfigurationExporter(config, node, "export")
    #    exporter.export()


if __name__ == '__main__':
    main(sys.argv[1:])
