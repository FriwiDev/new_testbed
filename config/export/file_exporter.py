import os
import shutil

from config.configuration import Configuration
from config.export.configuration_exporter import ConfigurationExporter
from topo.node import Node


class FileConfigurationExporter(ConfigurationExporter):
    def __init__(self, configuration: Configuration, node: Node, export_dir: str):
        super().__init__(configuration, node)
        self.export_dir = export_dir

    def export(self):
        if len(self.config.start_instructions) > 0 or len(self.config.stop_instructions) > 0:
            raise Exception("File exporter does not support instructions!")

        dir = self.export_dir + "/" + self.node.name
        if os.path.exists(dir) and os.path.isdir(dir):
            shutil.rmtree(dir)
        os.makedirs(dir)

        start_script = open(dir + "/start.sh", "w")
        start_script.write("#!/bin/bash\n\n")
        for i in range(0, len(self.config.start_cmds)):
            start_script.write(self.config.start_cmds[i].to_str() + "\n")
        start_script.close()

        stop_script = open(dir + "/stop.sh", "w")
        stop_script.write("#!/bin/bash\n\n")
        for i in range(0, len(self.config.stop_cmds)).__reversed__():
            stop_script.write(self.config.stop_cmds[i].to_str() + "\n")
        stop_script.close()

        for file in self.config.files:
            out = open(dir + "/" + file.name, "w")
            out.write(file.to_str())
            out.close()
