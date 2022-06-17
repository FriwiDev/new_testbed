from topo.node import Node
from topo.service import Service


class Link(object):
    def __init__(self, service1: Service, service2: Service,
                 port1: int = None, port2: int = None,
                 intf_name1: str = None, intf_name2: str = None,
                 mac_addr1: str = None, mac_addr2: str = None):
        self.service1 = service1
        self.service2 = service2
        self.port1 = port1 if port1 else service1.executor.new_port(service1)
        self.port2 = port2 if port2 else service2.executor.new_port(service2)
        self.intf_name1 = intf_name1 if intf_name1 else Link.inf_name(service1.executor, port1)
        self.intf_name2 = intf_name2 if intf_name2 else Link.inf_name(service2.executor, port2)
        self.mac_addr1 = mac_addr1  # TODO default initialization
        self.mac_addr2 = mac_addr2

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'service1': self.service1.name,
            'service2': self.service2.name,
            'port1': self.port1,
            'port2': self.port2,
            'intf_name1': self.intf_name1,
            'intf_name2': self.intf_name2,
            'mac_addr1': self.mac_addr1,
            'mac_addr2': self.mac_addr2  # ,
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Link':
        """Internal method to initialize from dictionary."""
        ret = Link(
            topo.get_service(in_dict['service1']),
            topo.get_service(in_dict['service2']),
            in_dict['port1'],
            in_dict['port2'],
            in_dict['intf_name1'],
            in_dict['intf_name2'],
            in_dict['mac_addr1'],
            in_dict['mac_addr2'])
        return ret

    @classmethod
    def inf_name(cls, executor: Node, port1: int) -> str:
        return executor.name + "-eth" + str(port1)
