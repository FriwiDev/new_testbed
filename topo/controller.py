import ipaddress
from abc import ABC

from config.configuration import Command
from platform.linux_server.lxc_service import LXCService
from topo.service import Service, ServiceType


class Controller(LXCService, ABC):
    def __init__(self, name: str, executor: 'Node', service_type: 'ServiceType', image: str = "ubuntu", cpu: str = None,
                 memory: str = None, ip: ipaddress.ip_address = ipaddress.ip_address("127.0.0.1"),
                 port: int = 6653, protocol: str = 'tcp'):
        super().__init__(name, executor, service_type, image, cpu, memory)
        self.ip = ip
        self.port = port
        self.protocol = protocol


class RyuController(Controller):
    def __init__(self, name: str, executor: 'Node', cpu: str = None, memory: str = None,
                 ip: ipaddress.ip_address = ipaddress.ip_address("127.0.0.1"), port: int = 6653, protocol: str = 'tcp',
                 script_path: str = None):
        super().__init__(name, executor, ServiceType.RYU, "ryu", cpu, memory, ip, port, protocol)
        self.script_path = script_path

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        log = f'/tmp/controller_{self.name}.log'
        if self.script_path is None:
            config.add_commmand(
                Command(self.lxc_prefix() +
                        f"ryu-manager --verbose &> {log} &"),
                Command(self.lxc_prefix() + "killall ryu-manager"))
        else:
            config.add_commmand(
                Command(self.lxc_prefix() +
                        f"ryu-manager --verbose {self.script_path} &> {log} &"),
                Command(self.lxc_prefix()+"killall ryu-manager"))
        pass
