from config.export.console_exporter import ConsoleConfigurationExporter
from platform.linux_server.linux_node import LinuxNode
from topo.link import Link
from topo.node import NodeType
from topo.service import Service, ServiceType
from topo.topo import Topo


class TestTopo(Topo):

    def create(self, *args, **params):
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN)
        self.add_node(node)
        service = Service(name="testservice", service_type=ServiceType.NONE, executor=node)
        self.add_service(service)
        self.add_link(Link(service1=service, service2=service))
        pass


def main():
    topo = TestTopo()
    # print(topo.export_topo())
    # print(Topo.import_topo(topo.export_topo()).export_topo())
    for name in topo.nodes:
        node = topo.nodes[name]
        config = node.get_configuration_builder(topo).build()
        exporter = ConsoleConfigurationExporter(config, node)
        exporter.export()


if __name__ == '__main__':
    main()
