import os
from os import PathLike
from pathlib import Path

from config.configuration import Configuration
from config.export.configuration_exporter import ConfigurationExporter
from ssh.output_consumer import PrintOutputConsumer
from ssh.ssh_command import SSHCommand, FileSendCommand
from topo.node import Node


class SSHConfigurationExporter(ConfigurationExporter):
    def __init__(self, configuration: Configuration, node: Node):
        super().__init__(configuration, node)

    def start_all(self, topo: 'Topo'):
        self._start_with_config(self.config, topo)

    def _start_with_config(self, config: Configuration, topo: 'Topo'):
        if len(config.start_instructions) > 0 or len(config.stop_instructions) > 0:
            raise Exception("SSH exporter does not support instructions!")

        for i in range(0, len(config.start_cmds)):
            if config.start_cmds[i].to_str().startswith("#filecopyafterlaunch"):
                service = config.start_cmds[i].to_str().split()[1]
                real_service = topo.services[service]
                if service in config.files.keys():
                    for file, dst in config.files[service]:
                        dst = str(dst)
                        if not dst.endswith("/"):
                            dst += "/"
                        self.copy(real_service, file, dst)
            elif config.start_cmds[i].to_str().startswith("#filecopybeforelaunch"):
                continue
            else:
                if not config.start_cmds[i].to_str() == "":
                    cmd = SSHCommand(self.node, config.start_cmds[i].to_str())
                    print(config.start_cmds[i].to_str())
                    cmd.add_consumer(PrintOutputConsumer())
                    cmd.run()
                    if cmd.exit_code is None or cmd.exit_code > 0:
                        raise Exception(f"Failed to run command: Exit code {cmd.exit_code}")

    def stop_all(self, topo: 'Topo'):
        self._stop_with_config(self.config, topo)

    def _stop_with_config(self, config: Configuration, topo: 'Topo'):
        if len(config.start_instructions) > 0 or len(config.stop_instructions) > 0:
            raise Exception("SSH exporter does not support instructions!")

        for i in range(0, len(config.stop_cmds)).__reversed__():
            if not config.stop_cmds[i].to_str() == "":
                cmd = SSHCommand(self.node, config.stop_cmds[i].to_str())
                print(config.stop_cmds[i].to_str())
                cmd.add_consumer(PrintOutputConsumer())
                cmd.run()

    def start(self, topo: 'Topo', builder: 'ConfigurationBuilder', service: 'Service'):
        config = builder.build_service(service)
        self._start_with_config(config, topo)

    def stop(self, topo: 'Topo', builder: 'ConfigurationBuilder', service: 'Service'):
        config = builder.build_service(service)
        self._stop_with_config(config, topo)

    def copy(self, service: 'Service', file: PathLike, base: str):
        if os.path.isdir(file):
            print("Creating dir " + str(file) + " on " + base + file.name)
            cmd = SSHCommand(self.node, service.command_prefix() + "mkdir -p \"" + base + file.name + "\"")
            cmd.run()
            if cmd.exit_code is None or cmd.exit_code > 0:
                raise Exception(f"Failed to create dir {base}{file.name} on remote machine: Exit code {cmd.exit_code}")
            # Copy children
            for sub in os.listdir(file):
                self.copy(service, Path(str(file) + "/" + str(sub)), base + file.name + "/")
        else:
            remote = base + file.name
            print("Uploading " + str(file) + " to " + remote)
            cmd = FileSendCommand(self.node, service.command_prefix(), str(os.path.abspath(file)), remote)
            cmd.add_consumer(PrintOutputConsumer())
            cmd.run()
            if cmd.exit_code is None or cmd.exit_code > 0:
                raise Exception(f"Failed to create file {remote} on remote machine: Exit code {cmd.exit_code}")
        pass
