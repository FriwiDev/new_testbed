from config.export.file_exporter import FileConfigurationExporter
from platform.linux_server.linux_node import LinuxNode
from topo.interface import Interface
from topo.link import Link
from topo.node import NodeType
from topo.service import Service, ServiceType
from topo.subnet import Subnet
from topo.switch import OVSSwitch
from topo.topo import Topo


class TestTopo(Topo):

    def create(self, *args, **params):
        subnet = Subnet("192.168.178.0/24")
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN)
        self.add_node(node)
        service1 = Service(name="service1", service_type=ServiceType.NONE, executor=node)
        service2 = Service(name="service2", service_type=ServiceType.NONE, executor=node)
        switch = OVSSwitch(name="switch1", executor=node)
        #service.add_interface(Interface("testintf").add_ip_from_subnet(subnet))
        self.add_service(service1)
        self.add_service(service2)
        self.add_service(switch)
        self.add_link(Link(self, service1=service1, service2=switch))
        self.add_link(Link(self, service1=switch, service2=service2))
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
