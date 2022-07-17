from config.export.file_exporter import FileConfigurationExporter
from platform.linux_server.linux_node import LinuxNode
from platform.linux_server.lxc_service import SimpleLXCHost
from topo.controller import RyuController
from topo.link import Link
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo


class TestTopo(Topo):

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
        self.add_link(Link(self, service1=ryu, service2=switch))
        self.add_link(Link(self, service1=host1, service2=switch))
        self.add_link(Link(self, service1=host2, service2=switch))
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
