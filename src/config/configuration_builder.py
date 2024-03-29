from abc import abstractmethod

from config.configuration import Configuration
from topo.node import Node
from topo.topo import Topo


class ConfigurationBuilder(object):
    def __init__(self, topo: Topo, node: Node):
        self.topo = topo
        self.node = node

    @abstractmethod
    def build(self) -> Configuration:
        """Implemented by every configuration builder to create a configuration for one node from a topology"""
        pass

    @abstractmethod
    def build_service(self, service: 'Service') -> Configuration:
        pass

    @abstractmethod
    def build_service_enable(self, service: 'Service') -> Configuration:
        pass

    @abstractmethod
    def build_base(self) -> Configuration:
        pass
