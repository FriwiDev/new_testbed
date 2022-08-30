from abc import ABC
from pathlib import Path

from config.configuration import Command
from platforms.linux_server.lxc_service import LXCService
from topo.service import ServiceType


class Controller(LXCService, ABC):
    def __init__(self, name: str, executor: 'Node', service_type: 'ServiceType', image: str = "ubuntu", cpu: str = None,
                 memory: str = None,
                 port: int = 6653, protocol: str = 'tcp'):
        super().__init__(name, executor, service_type, image, cpu, memory)
        self.port = port
        self.protocol = protocol

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(Controller, self).to_dict(), **{
            'port': str(self.port),
            'protocol': self.protocol
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Controller':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.port = int(in_dict['port'])
        ret.protocol = in_dict['protocol']
        return ret


class RyuController(Controller):
    def __init__(self, name: str, executor: 'Node', cpu: str = None, memory: str = None,
                 port: int = 6653, protocol: str = 'tcp',
                 script_path: str = None):
        super().__init__(name, executor, ServiceType.RYU, "ryu", cpu, memory, port, protocol)
        self.script_path = script_path

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        super().append_to_configuration(config_builder, config)
        if self.script_path is None:
            self.script_path = "/tmp/simple_switch.py"
            config.add_file(Path("defaults"))
            config.add_command(self.file_copy("defaults/simple_switch.py", "/tmp"), Command())
        log = f'/tmp/controller_{self.name}.log'
        if self.script_path is None:
            config.add_command(
                Command(self.lxc_prefix() +
                        f"ryu-manager --verbose &> {log} &"),
                Command(self.lxc_prefix() + "killall ryu-manager"))
        else:
            config.add_command(
                Command(self.lxc_prefix() +
                        f"ryu-manager --verbose {self.script_path} &> {log} &"),
                Command(self.lxc_prefix() + "killall ryu-manager"))
        pass

    def is_switch(self) -> bool:
        return False

    def is_controller(self) -> bool:
        return True

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(RyuController, self).to_dict(), **{
            'script_path': self.script_path
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'RyuController':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.script_path = in_dict['script_path']
        return ret
