from abc import abstractmethod, ABC

from config.configuration import Configuration
from network.network_address_generator import NetworkAddressGenerator
from topo.node import Node


class NetworkImplementation(ABC):
    def __init__(self, network_address_generator: NetworkAddressGenerator):
        self.network_address_generator = network_address_generator

    @abstractmethod
    def configure(self, topo: 'Topo'):
        pass

    @abstractmethod
    def generate(self, node: Node, config: Configuration):
        pass

    def get_network_address_generator(self) -> NetworkAddressGenerator:
        return self.network_address_generator

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'network_address_generator': self.network_address_generator.to_dict()
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'NetworkImplementation':
        """Internal method to initialize from dictionary."""
        raise Exception("Can not initialize abstract network implementation class")
