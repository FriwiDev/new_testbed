from enum import Enum

from topo.interface import Interface


class NodeType(Enum):
    LINUX_DEBIAN, LINUX_ARCH = range(2)


class Node(object):
    # name: str, node_type: NodeType
    def __init__(self, *args, **params):
        # Init from json when receiving dict
        if args and len(args) > 0\
                and args[0] and isinstance(args[0], dict):
            self._init_from_dict(args[0])
            return
        # Init normally else
        # TODO Check presence and include hinted optional params above
        self.name = params['name']
        self.type = params['node_type']
        self.intfs: list[Interface] = [Interface(name="lo").add_ip("127.0.0.1", "255.0.0.0")]

    def _init_from_dict(self, in_dict: dict):
        """Internal method to initialize from dictionary."""
        self.name = in_dict['name']
        self.type = NodeType[in_dict['type']]
        self.intfs = []
        for intf in in_dict['intfs']:
            self.intfs.append(Interface(intf))

    def add_interface(self, intf: Interface) -> repr("Node"):
        for i in self.intfs:
            if i.name == intf:
                raise Exception(f"Interface with name {intf.name} already exists in node {self.name}")
        self.intfs.append(intf)
        return self

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

    def new_port(self):
        # TODO
        pass
