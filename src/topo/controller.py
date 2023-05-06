from abc import ABC
from pathlib import Path

from config.configuration import Command
from platforms.linux_server.lxc_service import LXCService
from topo.service import ServiceType


class Controller(LXCService, ABC):
    """A controller is a service providing instructions to an OpenFlow switch."""

    def __init__(self, name: str, executor: 'Node', service_type: 'ServiceType', image: str = "ubuntu", cpu: str = None,
                 cpu_allowance: str = None, memory: str = None,
                 port: int = 6653, protocol: str = 'tcp'):
        """name: name for service
           executor: node this service is running on
           service_type: the type of this service for easier identification
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)
           port: the port to bind to (for switches to connect)
           protocol: typically tcp or udp"""
        super().__init__(name, executor, service_type, image, cpu, cpu_allowance, memory)
        self.port = port
        self.protocol = protocol

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(Controller, self).to_dict(without_gui), **{
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
    """A ryu controller."""

    def __init__(self, name: str, executor: 'Node', cpu: str = None, cpu_allowance: str = None, memory: str = None,
                 port: int = 6653, protocol: str = 'tcp',
                 script_path: str = "../examples/defaults/simple_switch.py"):
        """name: name for service
           executor: node this service is running on
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)
           port: the port to bind to (for switches to connect)
           protocol: typically tcp or udp
           script_path: the script (relative to your topology script) to use for this controller.
                        The whole folder the script is in will be copied"""
        super().__init__(name, executor, ServiceType.RYU, "ryu", cpu, cpu_allowance, memory, port, protocol)
        p = Path(script_path)
        if p.is_file():
            self.script_path = "/tmp/" + p.parent.name + "/" + p.name
            p = p.parent
            self.add_file(p.absolute(), Path("/tmp"))
        elif p.is_dir():
            self.script_path = "/tmp/" + p.name
            self.add_file(p.absolute(), Path("/tmp"))
        else:
            # We use a default config that is already on the controller
            self.script_path = script_path

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        log = f'/tmp/controller_{self.name}.log'
        if self.script_path is None:
            config.add_command(
                Command(self.lxc_prefix() +
                        f"ryu-manager --verbose --ofp-tcp-listen-port {self.port} &> {log} &"),
                Command(self.lxc_prefix() + "killall ryu-manager"))
        else:
            config.add_command(
                Command(self.lxc_prefix() +
                        f"ryu-manager --verbose {self.script_path} --ofp-tcp-listen-port {self.port} &> {log} &"),
                Command(self.lxc_prefix() + "killall ryu-manager"))

    def is_switch(self) -> bool:
        return False

    def is_controller(self) -> bool:
        return True

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(RyuController, self).to_dict(without_gui), **{
            'script_path': self.script_path
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'RyuController':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.script_path = in_dict['script_path']
        return ret
