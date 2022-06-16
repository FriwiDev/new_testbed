from abc import abstractmethod

from config.configuration import Configuration
from topo.node import Node


class NetworkImplementation(object):
    @abstractmethod
    def configure(self, topo: 'Topo'):
        pass

    @abstractmethod
    def generate(self, node: Node, config: Configuration):
        pass

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'NetworkImplementation':
        """Internal method to initialize from dictionary."""
        raise Exception("Can not initialize abstract network implementation class")
