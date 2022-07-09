from config.configuration import Configuration
from config.configuration_builder import ConfigurationBuilder
from topo.node import Node
from topo.topo import Topo


class LinuxConfigurationBuilder(ConfigurationBuilder):
    def __init__(self, topo: Topo, node: Node):
        super().__init__(topo, node)

    def build(self) -> Configuration:
        # TODO emit an actual configuration
        config = Configuration()
        # Generate network infrastructure
        self.topo.network_implementation.generate(self.node, config)
        # Generate our own containers
        for service in self.topo.services.values():
            if service.executor == self.node:
                service.append_to_configuration(self, config)
        # config.add_command(Command("startcommand"), Command("stopcommand"))
        # file = File("testfile")
        # file.append("Hello world! :)")
        # config.add_file(file)
        # config.add_instruction(Instruction("startinst"), Instruction("stopinst"))
        return config
