import json
from abc import abstractmethod

from topo.link import Link
from topo.node import Node
from topo.service import Service


class Topo(object):
    def __init__(self, *args, **params):
        # Init from json when receiving dict
        if 'skip_constructor' in params:
            return
        # Init normally else
        self.nodes = {}
        self.links = []
        self.services = {}
        self.network_implementation = params.pop('network_implementation', {})  # TODO Add default
        self.create(*args, **params)

    @classmethod
    def from_dict(cls, in_dict: dict, sel = None):
        """Internal method to initialize from dictionary."""
        if not sel:
            sel = Topo(skip_constructor=True)
        sel.nodes = {}
        for x in in_dict['nodes']:
            sel.nodes[x['name']] = eval(x['class'])(x)  # TODO Use an internal dict
        sel.services = {}
        for x in in_dict['services']:
            sel.services[x['name']] = eval(x['class'])(sel, x)  # TODO Use an internal dict
        sel.links = []
        for x in in_dict['links']:
            sel.links.append(eval(x['class'])(sel, x))  # TODO Use an internal dict

    def to_dict(self) -> dict:
        nodes = []
        for n in self.nodes:
            nodes.append(self.nodes[n].to_dict())
        services = []
        for s in self.services:
            services.append(self.services[s].to_dict())
        links = []
        for l in self.links:
            links.append(l.to_dict())
        return {
            'nodes': nodes,
            'services': services,
            'links': links
        }

    def export_topo(self):
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def import_topo(cls, in_json: str) -> 'Topo':
        return Topo(json.loads(in_json))

    @abstractmethod
    def create(self, *args, **params):
        pass

    def add_service(self, service: Service):
        if service.executor.name not in self.nodes:
            raise Exception(f"Node for service {service.name} was not added yet. Add nodes before services!")
        if service.name in self.services:
            raise Exception(f"Service with name {service.name} already exists")
        self.services[service.name] = service

    def get_service(self, name: str) -> Service:
        if name not in self.services:
            raise Exception(f"Service with name {name} does not exist")
        return self.services[name]

    def add_node(self, node: Node):
        if node.name in self.nodes:
            raise Exception(f"Node with name {node.name} already exists")
        self.nodes[node.name] = node

    def get_node(self, name: str) -> Node:
        if name not in self.nodes:
            raise Exception(f"Node with name {name} does not exist")
        return self.nodes[name]

    def add_link(self, link: Link):
        if link in self.links:
            raise Exception("Link was already added")
        self.links.append(link)

    def get_links(self, service1: Service, service2: Service) -> list[Link]:
        return [link for link in self.links
                if (link.service1, link.service2) in ((service1, service2), (service2, service1))]
