from enum import Enum


class ServiceType(Enum):
    NONE = range(1)


class Service(object):
    # name: str, service_type: ServiceType, executor: Node
    def __init__(self, *args, **params):
        # Init from json when receiving dict
        if args and len(args) > 1 \
                and args[0]\
                and args[1] and isinstance(args[1], dict):
            self._init_from_dict(args[0], args[1])
            return
        # Init normally else
        # TODO Check presence and include hinted optional params above
        self.name = params['name']
        self.type = params['service_type']
        self.executor = params['executor']

    def _init_from_dict(self, topo: 'Topo', in_dict: dict):
        """Internal method to initialize from dictionary."""
        self.name = in_dict['name']
        self.executor = topo.get_node(in_dict['executor'])
        self.type = ServiceType[in_dict['type']]

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'name': self.name,
            'executor': self.executor.name,
            'type': self.type.name
        }
