from abc import abstractmethod
from enum import Enum

from topo.interface import Interface
from topo.node import Node


class ServiceType(Enum):
    NONE, OVS, RYU = range(3)


class Service(object):
    def __init__(self, name: str, executor: Node, service_type: ServiceType = None):
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

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        """Method to be implemented by every service definition"""
        pass

    def get_interface(self, intf_name: str) -> Interface:
        for i in self.intfs:
            if i.name == intf_name:
                return i
        return None

    def add_interface_by_name(self, intf_name: str) -> Interface:
        i = Interface(intf_name)
        self.add_interface(i)
        return i
