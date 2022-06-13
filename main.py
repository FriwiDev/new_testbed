from topo.link import Link
from topo.node import NodeType, Node
from topo.service import Service, ServiceType
from topo.topo import Topo


class TestTopo(Topo):

    def create(self, *args, **params):
        node = Node(name="testnode", node_type=NodeType.LINUX_DEBIAN)
        self.add_node(node)
        service = Service(name="testservice", service_type=ServiceType.NONE, executor=node)
        self.add_service(service)
        self.add_link(Link(service1=service, service2=service))
        pass


def main():
    topo = TestTopo()
    print(topo.export_topo())
    print(Topo.import_topo(topo.export_topo()).export_topo())


if __name__ == '__main__':
    main()
