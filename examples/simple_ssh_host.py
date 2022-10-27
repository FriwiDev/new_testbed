import sys

from extensions.macvlan_extension_builder import MacVlanExtensionBuilder
from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.interface import Interface
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.topo import Topo, TopoUtil


# Simple topology with two hosts that are connected.
# Host1 exposes an ssh daemon on a public macvlan. Can be connected to from any OTHER host than the host machine,
# using key authentication.
class SimpleSSHHost(Topo):

    def __init__(self, *args, **params):
        super().__init__(args=args, **params)

    def create(self, *args, **params):
        # Create a node to execute on
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        # Add interface to node - we need it later to set up the macvlan device
        node.add_interface(Interface("enp3s0"))
        self.add_node(node)
        # Create and append all services (two hosts)
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(host1)
        self.add_service(host2)
        # Create links between host1 <-> host2
        link = Link(self, service1=host1, service2=host2, link_type=LinkType.VXLAN)
        self.add_link(link)
        # Create macvlan port on host1 and selecting the node port to bind on (enp3s0)
        # Public key is appended as string as seen below
        MacVlanExtensionBuilder(node.get_interface("enp3s0"), host1,
                                "ssh-rsa "
                                "AAAAB3NzaC1yc2EAAAADAQABAAABgQC1ykQLXsgAujgAn9Sy9RbwGjsBvOzDuXmxOcSSjZ75D1nomjA9Hcc4Nn"
                                "A0+GK1kW69GbsZ+zPlbnW+moL6B6uelA5efb7lCpqS9SMaxQbtrE9jrNP68zYrqz3EcPU9niB7Bge0DGCspvg8"
                                "x+YoLyy1+eVVVN2809SrNIfIjELwtiJb7rSAm0JiABtU8w5Q6lrbY4zpIZxfs2F7C/gc9UpuCSje5ujELBxTDH"
                                "XK2eX7C0w4KJtJvOp0SVHluZwWu3jcpVyuQM9TQiwyAkD+ai37mET2cvYGmXaGSWlS02ALgA63LxNQQQ8s15PK"
                                "hdzCuPtg/lv1UV6FCUrISxH08bfytI4Z4FTTb3Xrcqn/HmmUDYWarcscnifHfa9K+LPpfchJLZdzP0TC9+cbne"
                                "9BfznJTokP6UK++ddbZraNf08zeJXhgDRwztYD4akfLHm+gSsB0tljrJLqz0DtxJTwpeDK8P+D3nadJcHS7JEK"
                                "x1dnm1syesbOVc1zSXDTxe4Gj6M=") \
            .build()
        pass


# Boilerplate code to export topology from ./generate_topology.sh script
def main(argv: list[str]):
    TopoUtil.run_build(argv, SimpleSSHHost)


if __name__ == '__main__':
    main(sys.argv)
