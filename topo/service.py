from enum import Enum

from topo.interface import Interface
from topo.node import Node


class ServiceType(Enum):
    NONE = range(1)


class Service(object):
    def __init__(self, name: str, service_type: ServiceType, executor: Node):
        self.name = name
        self.type = service_type
        self.executor = executor
        self.intfs: list[Interface] = []

    def add_interface(self, intf: Interface) -> 'Service':
        for i in self.intfs:
            if i.name == intf:
                raise Exception(f"Interface with name {intf.name} already exists in service {self.name}")
        self.intfs.append(intf)
        return self

    def to_dict(self) -> dict:
        intfs = []
        for i in self.intfs:
            intfs.append(i.to_dict())
        return {
            'class': type(self).__name__,
            'name': self.name,
            'executor': self.executor.name,
            'type': self.type.name,
            'intfs': self.intfs
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Service':
        """Internal method to initialize from dictionary."""
        ret = Service(in_dict['name'],
                      ServiceType[in_dict['type']],
                      topo.get_node(in_dict['executor']))
        for intf in in_dict['intfs']:
            ret.intfs.append(Interface(intf))
        return ret
