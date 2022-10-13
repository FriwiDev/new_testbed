import sys

from extensions.macvlan_extension_builder import MacVlanExtensionBuilder
from extensions.wireguard_extension_builder import WireguardExtensionBuilder
from network.default_network_implementation import DefaultNetworkImplementation
from platforms.linux_server.linux_node import LinuxNode
from platforms.linux_server.lxc_service import SimpleLXCHost
from topo.interface import Interface
from topo.link import Link, LinkType
from topo.node import NodeType
from topo.switch import OVSSwitch
from topo.topo import Topo


class TestTopo(Topo):

    def __init__(self, *args, **params):
        super().__init__(network_implementation=DefaultNetworkImplementation("10.0.0.0/24", "239.1.1.1"),
                         *args, **params)

    def create(self, *args, **params):
        node = LinuxNode(name="testnode", node_type=NodeType.LINUX_DEBIAN, ssh_remote="root@localhost")
        node.add_interface(Interface("wlp2s0").add_ip("10.0.1.28", "10.0.1.0/24")) \
            .add_interface(Interface("enp3s0").add_ip("10.0.1.4", "10.0.1.0/24"))
        self.add_node(node)
        # node1 = LinuxNode(name="testnode1", node_type=NodeType.LINUX_DEBIAN)
        # node1.add_interface(Interface("wlp2s0").add_ip("10.0.1.29", "10.0.1.0/24")) \
        #    .add_interface(Interface("enp3s0").add_ip("10.0.1.5", "10.0.1.0/24"))
        # self.add_node(node1)
        switch1 = OVSSwitch(name="switch1", executor=node, fail_mode='standalone')
        host1 = SimpleLXCHost(name="host1", executor=node)
        host2 = SimpleLXCHost(name="host2", executor=node)
        self.add_service(switch1)
        self.add_service(host1)
        self.add_service(host2)
        link1 = Link(self, service1=host1, service2=switch1, link_type=LinkType.DIRECT)
        link2 = Link(self, service1=switch1, service2=host2, link_type=LinkType.VXLAN)
        self.add_link(link1)
        self.add_link(link2)
        # self.network_implementation.set_link_interface_mapping(link1, "enp3s0", "enp3s0")
        # self.network_implementation.set_link_interface_mapping(link2, "wlp2s0", "wlp2s0")
        WireguardExtensionBuilder(host1, host2, link1.intf1, link2.intf2,
                                  "192.168.178.1", "192.168.178.2", "192.168.178.0/24") \
            .build()
        MacVlanExtensionBuilder(node.get_interface("enp3s0"), host1,
                                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC1ykQLXsgAujgAn9Sy9RbwGjsBvOzDuXmxOcSSjZ75D1nomjA9Hcc4NnA0+GK1kW69GbsZ+zPlbnW+moL6B6uelA5efb7lCpqS9SMaxQbtrE9jrNP68zYrqz3EcPU9niB7Bge0DGCspvg8x+YoLyy1+eVVVN2809SrNIfIjELwtiJb7rSAm0JiABtU8w5Q6lrbY4zpIZxfs2F7C/gc9UpuCSje5ujELBxTDHXK2eX7C0w4KJtJvOp0SVHluZwWu3jcpVyuQM9TQiwyAkD+ai37mET2cvYGmXaGSWlS02ALgA63LxNQQQ8s15PKhdzCuPtg/lv1UV6FCUrISxH08bfytI4Z4FTTb3Xrcqn/HmmUDYWarcscnifHfa9K+LPpfchJLZdzP0TC9+cbne9BfznJTokP6UK++ddbZraNf08zeJXhgDRwztYD4akfLHm+gSsB0tljrJLqz0DtxJTwpeDK8P+D3nadJcHS7JEKx1dnm1syesbOVc1zSXDTxe4Gj6M=") \
            .build()
        pass


def main(argv: list[str]):
    topo = TestTopo()
    # Serialize to stdout
    print(topo.export_topo())


if __name__ == '__main__':
    main(sys.argv[1:])
