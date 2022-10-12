from platforms.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from topo.node import Node, NodeType


class LinuxNode(Node):
    def __init__(self, name: str, node_type: NodeType, ssh_remote: str, ssh_port: int = 22,
                 ssh_work_dir: str = None):
        super().__init__(name, node_type, ssh_remote, ssh_port, ssh_work_dir)

    def get_configuration_builder(self, topo: 'Topo'):
        return LinuxConfigurationBuilder(topo, self)
