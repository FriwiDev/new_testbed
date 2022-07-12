import ipaddress
from abc import ABC

from config.configuration import Command
from topo.service import Service, ServiceType


class Controller(Service, ABC):
    def __init__(self, name: str, executor: 'Node', service_type: 'ServiceType',
                 ip: ipaddress.ip_address = ipaddress.ip_address("127.0.0.1"), port: int = 6653, protocol: str = 'tcp'):
        super().__init__(name, executor, service_type)
        self.ip = ip
        self.port = port
        self.protocol = protocol


class RyuController(Controller):
    def __init__(self, name: str, executor: 'Node',
                 ip: ipaddress.ip_address = ipaddress.ip_address("127.0.0.1"), port: int = 6653, protocol: str = 'tcp'):
        super().__init__(name, ServiceType.RYU, executor, ip, port, protocol)

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        log = '/tmp/controller_{}.log'.format(self.name)
        config.add_commmand(
            Command("nohup /usr/local/bin/ryu-manager "
                    "--verbose /usr/local/lib/python2.7/dist-packages/ryu/app/simple_switch_13.py &> {} &"
                    .format(log)
                    ),
            Command("killall ryu-manager"))
        pass
