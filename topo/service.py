from enum import Enum

from topo.node import Node


class ServiceType(Enum):
    NONE = range(1)


class Service(object):
    def __init__(self, name: str, service_type: ServiceType, executor: Node):
        self.name = name
        self.type = service_type
        self.executor = executor

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'name': self.name,
            'executor': self.executor.name,
            'type': self.type.name
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Service':
        """Internal method to initialize from dictionary."""
        ret = Service(in_dict['name'],
                      ServiceType[in_dict['type']],
                      topo.get_node(in_dict['executor']))
        return ret
