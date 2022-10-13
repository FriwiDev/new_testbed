import ipaddress

from config.configuration import Command
from extensions.service_extension import ServiceExtension
from extensions.wireguard_keygen import WireguardKeygen
from network.network_utils import NetworkUtils
from topo.interface import Interface


class WireguardServiceExtension(ServiceExtension):
    def __init__(self, name: str, service: 'Service'):
        super().__init__(name, service)
        self.private_key: str = None
        self.public_key: str = None
        self.dev_name: str = None
        self.ip: ipaddress.ip_address = None
        self.network: ipaddress.ip_network = None
        self.intf: Interface = None
        self.port: int = None
        self.remote_service: 'Service' = None
        self.remote_service_name: str = None
        self.remote_wireguard_extension: 'WireguardServiceExtension' = None
        self.remote_wireguard_extension_name: str = None
        if self.dev_name:
            self.claimed_interfaces.append(self.dev_name)

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(WireguardServiceExtension, self).to_dict(), **{
            'priv': self.private_key,
            'pub': self.public_key,
            'dev': self.dev_name,
            'ip': str(self.ip),
            'net': str(self.network),
            'intf': self.intf.name,
            'port': str(self.port),
            'remote_service': self.remote_service_name,
            'remote_wireguard_extension': self.remote_wireguard_extension_name
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict, service: 'Service') -> 'WireguardServiceExtension':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict, service)
        ret.private_key = in_dict['priv']
        ret.public_key = in_dict['pub']
        ret.dev_name = in_dict['dev']
        ret.ip = ipaddress.ip_address(in_dict['ip'])
        ret.network = ipaddress.ip_network(in_dict['net'])
        ret.intf = service.get_interface(in_dict['intf'])
        ret.port = int(in_dict['port'])
        ret.remote_service_name = in_dict['remote_service']
        ret.remote_wireguard_extension_name = in_dict['remote_wireguard_extension']
        ret.claimed_interfaces.append(ret.dev_name)
        return ret

    def gen_keys(self):
        gen = WireguardKeygen()
        gen.gen_keys()
        self.private_key = gen.private_key
        self.public_key = gen.public_key

    def append_to_configuration(self, prefix: str, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        self.remote_service = config_builder.topo.get_service(self.remote_service_name)
        self.remote_wireguard_extension = self.remote_service.extensions[self.remote_wireguard_extension_name]

        filename = f"priv_key_{self.dev_name}.txt"
        if len(self.remote_wireguard_extension.intf.ips) == 0:
            raise Exception("Remote interface for wireguard tunnel must not have no assigned ips")
        remote_ip = self.remote_wireguard_extension.intf.ips[0]

        config.add_command(Command(f"{prefix} ip link add dev {self.dev_name} type wireguard"),
                           Command(f"{prefix} ip link del {self.dev_name}"))
        NetworkUtils.add_ip(config, self.dev_name, self.ip, self.network, prefix)
        config.add_command(Command(f"{prefix} bash -c \"echo \\\"{self.remote_wireguard_extension.private_key}\\\" "
                                   f"> {filename}\""),
                           Command())
        config.add_command(Command(f"{prefix} wg set {self.dev_name} listen-port {self.port} private-key ./{filename} "
                                   f"peer {self.public_key} allowed-ips {str(self.network)} "
                                   f"endpoint {str(remote_ip)}:{self.remote_wireguard_extension.port}"),
                           Command())
        NetworkUtils.set_up(config, self.dev_name, prefix)

    def append_to_configuration_pre_start(self, prefix: str, config_builder: 'ConfigurationBuilder',
                                          config: 'Configuration'):
        pass
