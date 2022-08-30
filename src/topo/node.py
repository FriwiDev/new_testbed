from abc import abstractmethod, ABC
from enum import Enum

from topo.interface import Interface


class NodeType(Enum):
    LINUX_DEBIAN, LINUX_ARCH = range(2)


class Node(ABC):
    def __init__(self, name: str, node_type: NodeType):
        self.name = name
        self.type = node_type
        self.intfs: list[Interface] = [Interface(name="lo").add_ip("127.0.0.1", "127.0.0.0/8")]
        self.current_virtual_device_num = 0

    def add_interface(self, intf: Interface) -> 'Node':
        for i in self.intfs:
            if i.name == intf:
                raise Exception(f"Interface with name {intf.name} already exists in node {self.name}")
        self.intfs.append(intf)
        return self

    def get_interface(self, intf: str) -> Interface:
        for i in self.intfs:
            if i.name == intf:
                return i
        return None

    def get_new_virtual_device_num(self) -> int:
        ret = self.current_virtual_device_num
        self.current_virtual_device_num += 1
        return ret

    @abstractmethod
    def get_configuration_builder(self, topo: 'Topo'):
        pass

    def to_dict(self) -> dict:
        intfs = []
        for i in self.intfs:
            intfs.append(i.to_dict())
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'name': self.name,
            'type': self.type.name,
            'current_virtual_device_num': str(self.current_virtual_device_num),
            'intfs': intfs
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Node':
        """Internal method to initialize from dictionary."""
        ret = cls(in_dict['name'],
                  NodeType[in_dict['type']])
        ret.current_virtual_device_num = int(in_dict['current_virtual_device_num'])
        ret.intfs.clear()
        for intf in in_dict['intfs']:
            ret.intfs.append(Interface.from_dict(intf))
        return ret
