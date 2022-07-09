from abc import abstractmethod
from enum import Enum

from topo.interface import Interface


class NodeType(Enum):
    LINUX_DEBIAN, LINUX_ARCH = range(2)


class Node(object):
    def __init__(self, name: str, node_type: NodeType):
        self.name = name
        self.type = node_type
        self.intfs: list[Interface] = [Interface(name="lo").add_ip("127.0.0.1", "127.0.0.0/8")]
        self.occupied_ports: dict[Interface, dict[int, 'Service']] = {}

    def add_interface(self, intf: Interface) -> 'Node':
        for i in self.intfs:
            if i.name == intf:
                raise Exception(f"Interface with name {intf.name} already exists in node {self.name}")
        self.intfs.append(intf)
        self.occupied_ports[intf] = {}
        return self

    def get_interface(self, intf: str) -> Interface:
        for i in self.intfs:
            if i.name == intf:
                return i
        return None

    def get_occupied_ports(self, intf: Interface) -> list[int]:
        return [i for i, _ in self.occupied_ports[intf].items()]

    def new_port(self, intf: Interface, service: 'Service') -> int:
        for i in range(1025, 65536):
            if i not in self.occupied_ports[intf]:
                self.occupied_ports[intf][i] = service
                return i
        raise Exception(f"No empty port left on interface {self.name}/{intf.name}")

    @abstractmethod
    def get_configuration_builder(self, topo: 'Topo'):
        pass

    def to_dict(self) -> dict:
        intfs = []
        for i in self.intfs:
            intfs.append(i.to_dict())
        return {
            'class': type(self).__name__,
            'name': self.name,
            'type': self.type.name,
            'intfs': intfs
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Node':
        """Internal method to initialize from dictionary."""
        ret = Node(in_dict['name'],
                   NodeType[in_dict['type']])
        for intf in in_dict['intfs']:
            ret.intfs.append(Interface(intf))
        return ret
