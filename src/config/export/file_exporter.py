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
            if self.config.start_cmds[i].to_str().startswith("#filecopybeforelaunch"):
                service = self.config.start_cmds[i].to_str().split()[1]
                if service in self.config.files.keys():
                    for file, dst in self.config.files[service]:
                        start_script.write(self.file_copy(service, service + "/" + file.name, str(dst)) + "\n")
            elif self.config.start_cmds[i].to_str().startswith("#filecopyafterlaunch"):
                continue
            else:
                if not self.config.start_cmds[i].to_str() == "":
                    start_script.write("echo \"" + self.config.start_cmds[i].to_str().replace("\\", "\\\\")
                                       .replace("\"", "\\\"") + "\"\n")
                    start_script.write(self.config.start_cmds[i].to_str() + "\n")
        start_script.close()
        os.chmod(dir + "/start.sh", os.stat(dir + "/start.sh").st_mode | stat.S_IEXEC)

        stop_script = open(dir + "/stop.sh", "w")
        stop_script.write("#!/bin/bash\n\n")
        for i in range(0, len(self.config.stop_cmds)).__reversed__():
            if not self.config.stop_cmds[i].to_str() == "":
                stop_script.write("echo \"" + self.config.stop_cmds[i].to_str().replace("\\", "\\\\")
                                  .replace("\"", "\\\"") + "\"\n")
                stop_script.write(self.config.stop_cmds[i].to_str() + "\n")
        stop_script.close()
        os.chmod(dir + "/stop.sh", os.stat(dir + "/stop.sh").st_mode | stat.S_IEXEC)

        for service in self.config.files.keys():
            for file, path in self.config.files[service]:
                FileConfigurationExporter._copy_tree(file, Path(dir + "/" + service + "/" + file.name))

    def file_copy(self, service: str, local_file: str, container_dir: str) -> str:
        if local_file.startswith("/"):
            raise Exception(f"Can not copy an absolute file path like {local_file} into container")
        if not container_dir.startswith("/"):
            raise Exception(f"Container path for copy to {service} is not absolute: {container_dir}")
        # Append / to prevent an avoidable error
        if not container_dir.endswith("/"):
            container_dir = container_dir + "/"
        return f"lxc file push -r $(dirname \"$0\")/{local_file} {service}{container_dir}"  # / is in container_dir

    @classmethod
    def _copy_tree(cls, src: os.PathLike, dst: os.PathLike):
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        try:
            shutil.copytree(src, dst)
        except OSError as exc:  # python >2.5
            if exc.errno in (errno.ENOTDIR, errno.EINVAL):
                shutil.copy(src, dst)
            else:
                raise
