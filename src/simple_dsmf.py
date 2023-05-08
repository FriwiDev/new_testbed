import sys

from platforms.linux_server.linux_node import LinuxNode
from topo.edgeslicing.dsmf_service import DSMFService
from topo.node import NodeType
from topo.topo import Topo, TopoUtil


# Simple topology with one switch connecting two hosts.
class SimpleDSMF(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        self.add_node(node)
        # Create and append all services (one switch and two hosts)
        dsmf = DSMFService(name="DSMF", executor=node)
        self.add_service(dsmf)
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, SimpleDSMF)


if __name__ == '__main__':
    main(sys.argv)
