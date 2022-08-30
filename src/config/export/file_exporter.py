import errno
import os
import shutil
import stat
from pathlib import Path

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
        start_script.write("#!/bin/bash\nset -e\n\n")
        for i in range(0, len(self.config.start_cmds)):
            start_script.write("echo \"" + self.config.start_cmds[i].to_str() + "\"\n")
            start_script.write(self.config.start_cmds[i].to_str() + "\n")
        start_script.close()
        os.chmod(dir + "/start.sh", os.stat(dir + "/start.sh").st_mode | stat.S_IEXEC)

        stop_script = open(dir + "/stop.sh", "w")
        stop_script.write("#!/bin/bash\n\n")
        for i in range(0, len(self.config.stop_cmds)).__reversed__():
            stop_script.write("echo \"" + self.config.stop_cmds[i].to_str() + "\"\n")
            stop_script.write(self.config.stop_cmds[i].to_str() + "\n")
        stop_script.close()
        os.chmod(dir + "/stop.sh", os.stat(dir + "/stop.sh").st_mode | stat.S_IEXEC)

        for file in self.config.files:
            FileConfigurationExporter._copy_tree(file, Path(dir + "/" + file.name))

    @classmethod
    def _copy_tree(cls, src: os.PathLike, dst: os.PathLike):
        try:
            shutil.copytree(src, dst)
        except OSError as exc:  # python >2.5
            if exc.errno in (errno.ENOTDIR, errno.EINVAL):
                shutil.copy(src, dst)
            else:
                raise
