from config.configuration import Configuration
from config.configuration_builder import ConfigurationBuilder
from topo.node import Node
from topo.topo import Topo


class LinuxConfigurationBuilder(ConfigurationBuilder):

    def __init__(self, topo: Topo, node: Node):
        super().__init__(topo, node)

    def build(self) -> Configuration:
        config = Configuration()
        # Generate network infrastructure
        self.topo.network_implementation.generate(self.node, config)
        # Generate our own containers
        for service in self.topo.services.values():
            if service.executor == self.node:
                service.append_to_configuration(self, config)
        return config

    def build_service(self, service: 'Service') -> Configuration:
        config = Configuration()
        service.append_to_configuration(self, config)
        return config

    def build_service_enable(self, service: 'Service') -> Configuration:
        config = Configuration()
        service.append_to_configuration_enable(self, config)
        return config

    def build_base(self) -> Configuration:
        config = Configuration()
        # Generate network infrastructure
        self.topo.network_implementation.generate(self.node, config)
        return config
