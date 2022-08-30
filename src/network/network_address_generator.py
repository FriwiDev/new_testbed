import ipaddress
from abc import ABC, abstractmethod

from topo.util import MacUtil


class NetworkAddressGenerator(ABC):
    @abstractmethod
    def generate_ip(self, service: 'Service', intf: 'Interface') -> ipaddress.ip_address:
        pass

    @abstractmethod
    def generate_network(self, service: 'Service', intf: 'Interface') -> ipaddress.ip_network:
        pass

    @abstractmethod
    def generate_mac(self, service: 'Service', intf: 'Interface') -> str:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'module': type(self).__module__
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'NetworkAddressGenerator':
        raise Exception("Can not initialize abstract NetworkAddressGenerator")


class BasicNetworkAddressGenerator(NetworkAddressGenerator):

    def __init__(self, network: ipaddress.ip_network or str, base_mac: int,
                 current_ip_index: int = -1, current_mac: int = -1):
        if isinstance(network, str):
            network = ipaddress.ip_network(network)
        self.network = network
        self.current_ip_index = 2 if current_ip_index == -1 else current_ip_index
        self.base_mac = base_mac
        self.current_mac = base_mac if current_mac == -1 else current_mac

    def generate_ip(self, service: 'Service', intf: 'Interface') -> ipaddress.ip_address:
        ret = ipaddress.ip_address(int(self.network.network_address) + self.current_ip_index)
        self.current_ip_index += 1
        return ret

    def generate_network(self, service: 'Service', intf: 'Interface') -> ipaddress.ip_network:
        return self.network

    def generate_mac(self, service: 'Service', intf: 'Interface') -> str:
        ret = MacUtil.mac_colon_hex(self.current_mac)
        self.current_mac += 1
        return ret

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(BasicNetworkAddressGenerator, self).to_dict(), **{
            'network': format(self.network),
            'current_ip_index': str(self.current_ip_index),
            'base_mac': str(self.base_mac),
            'current_mac': str(self.current_mac)
        }}

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'BasicNetworkAddressGenerator':
        """Internal method to initialize from dictionary."""
        ret = BasicNetworkAddressGenerator(ipaddress.ip_network(in_dict['network']),
                                           int(in_dict['base_mac']),
                                           int(in_dict['current_ip_index']),
                                           int(in_dict['current_mac']))
        return ret
