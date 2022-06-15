from config.configuration import Configuration, Command, File, Instruction
from config.configuration_builder import ConfigurationBuilder
from topo.node import Node
from topo.topo import Topo


class LinuxConfigurationBuilder(ConfigurationBuilder):
    def __init__(self, topo: Topo, node: Node):
        super().__init__(topo, node)

    def build(self) -> Configuration:
        # TODO emit an actual configuration
        config = Configuration()
        config.add_command(Command("startcommand"), Command("stopcommand"))
        file = File("testfile")
        file.append("Hello world! :)")
        config.add_file(file)
        config.add_instruction(Instruction("startinst"), Instruction("stopinst"))
        return config
