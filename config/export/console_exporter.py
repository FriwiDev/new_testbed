from config.configuration import Configuration
from config.export.configuration_exporter import ConfigurationExporter
from topo.node import Node


class ConsoleConfigurationExporter(ConfigurationExporter):
    def __init__(self, configuration: Configuration, node: Node):
        super().__init__(configuration, node)

    def export(self):
        print(f"Export dump for node: {self.node.name}")
        print("Commands:")
        for i in range(0, len(self.config.start_cmds)):
            print(f"{self.config.start_cmds[i].to_str()} <-|-> {self.config.stop_cmds[i].to_str()}")
        print("No commands" if len(self.config.start_cmds) == 0 else "")

        print("Instructions:")
        for i in range(0, len(self.config.start_instructions)):
            print(f"{self.config.start_instructions[i].to_str()} <-|-> {self.config.stop_instructions[i].to_str()}")
        print("No instructions" if len(self.config.start_instructions) == 0 else "")

        print("Files:")
        for file in self.config.files:
            print(file.to_str())
        print("No files" if len(self.config.files) == 0 else "")
