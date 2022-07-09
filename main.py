from config.export.file_exporter import FileConfigurationExporter
from platform.linux_server.linux_node import LinuxNode
from topo.interface import Interface
from topo.link import Link
from topo.node import NodeType
from topo.service import Service, ServiceType
from topo.subnet import Subnet
from topo.topo import Topo


class TestTopo(Topo):

    def create(self, *args, **params):
        subnet = Subnet("192.168.178.0/24")
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN)
        self.add_node(node)
        service = Service(name="testservice", service_type=ServiceType.NONE, executor=node)
        service.add_interface(Interface("testintf").add_ip_from_subnet(subnet))
        self.add_service(service)
        self.add_link(Link(self, service1=service, service2=service))
        pass


def main():
    topo = TestTopo()
    # print(topo.export_topo())
    # print(Topo.import_topo(topo.export_topo()).export_topo())
    for name in topo.nodes:
        node = topo.nodes[name]
        config = node.get_configuration_builder(topo).build()
        exporter = FileConfigurationExporter(config, node, "export")
        exporter.export()


if __name__ == '__main__':
    main()
