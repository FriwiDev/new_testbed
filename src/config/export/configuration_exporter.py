from config.configuration import Configuration
from topo.node import Node


class ConfigurationExporter(object):
    def __init__(self, configuration: Configuration, node: Node):
        self.config = configuration
        self.node = node

