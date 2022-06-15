from abc import abstractmethod

from config.configuration import Configuration
from topo.node import Node


class ConfigurationExporter(object):
    def __init__(self, configuration: Configuration, node: Node):
        self.config = configuration
        self.node = node

    @abstractmethod
    def export(self):
        """Implemented by every configuration exporter to export a configuration for one node to the desired format"""
        pass
