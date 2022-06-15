from platform.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from topo.node import Node, NodeType


class LinuxNode(Node):
    def __init__(self, name: str, node_type: NodeType):
        super().__init__(name, node_type)

    def get_configuration_builder(self, topo: 'Topo'):
        return LinuxConfigurationBuilder(topo, self)
