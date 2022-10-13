import ipaddress

from extensions.wireguard_extension import WireguardServiceExtension
from topo.interface import Interface


class WireguardExtensionBuilder(object):
    def __init__(self, service1: 'Service', service2: 'Service',
                 intf1: 'Interface', intf2: 'Interface',
                 ip1: ipaddress.ip_address or str, ip2: ipaddress.ip_address or str,
                 network: ipaddress.ip_network or str,
                 dev_name1: str = "wg0", dev_name2: str = "wg1",
                 port1: int = 1337, port2: int = 1337):
        if isinstance(ip1, str):
            ip1 = ipaddress.ip_address(ip1)
        if isinstance(ip2, str):
            ip2 = ipaddress.ip_address(ip2)
        if isinstance(network, str):
            network = ipaddress.ip_network(network)
        self.service1 = service1
        self.service2 = service2
        self.intf1 = intf1
        self.intf2 = intf2
        self.ip1 = ip1
        self.ip2 = ip2
        self.network = network
        self.dev_name1 = dev_name1
        self.dev_name2 = dev_name2
        self.port1 = port1
        self.port2 = port2

    def build(self):
        ext1 = WireguardServiceExtension(self.dev_name1, self.service1)
        ext1.dev_name = self.dev_name1
        ext1.ip = self.ip1
        ext1.network = self.network
        ext1.intf = self.intf1
        ext1.port = self.port1
        ext1.remote_service = self.service2
        ext1.remote_service_name = self.service2.name
        self.service1.intfs.append(Interface(self.dev_name1).add_ip(self.ip1, self.network))

        ext2 = WireguardServiceExtension(self.dev_name2, self.service2)
        ext2.dev_name = self.dev_name2
        ext2.ip = self.ip2
        ext2.network = self.network
        ext2.intf = self.intf2
        ext2.port = self.port2
        ext2.remote_service = self.service1
        ext2.remote_service_name = self.service1.name
        self.service2.intfs.append(Interface(self.dev_name2).add_ip(self.ip2, self.network))

        ext1.remote_wireguard_extension = ext2
        ext1.remote_wireguard_extension_name = ext2.name
        ext2.remote_wireguard_extension = ext1
        ext2.remote_wireguard_extension_name = ext1.name

        ext1.gen_keys()
        ext2.gen_keys()

        self.service1.add_extension(ext1)
        self.service2.add_extension(ext2)
