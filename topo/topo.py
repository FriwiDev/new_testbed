import json
from abc import abstractmethod

from network.vxlan_network import VxLanNetworkImplementation
from topo.link import Link
from topo.node import Node
from topo.service import Service
from topo.util import MacUtil


class Topo(object):
    def __init__(self, nodes: dict[str, Node] = {},
                 links: list[Link] = [],
                 services: dict[str, Service] = {},
                 network_implementation: 'NetworkImplementation' = VxLanNetworkImplementation("239.1.1.1"),
                 *args, **params):
        self.mac_util = MacUtil()
        self.nodes = nodes
        self.links = links
        self.services = services
        self.network_implementation = network_implementation
        self.create(args, params)
        self.network_implementation.configure(self)

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
            'links': links,
            'network_implementation': self.network_implementation.to_dict()
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Topo':
        """Internal method to initialize from dictionary."""
        ret = Topo()
        for x in in_dict['nodes']:
            ret.nodes[x['name']] = eval(x['class']).from_dict(x)  # TODO Use an internal dict
        for x in in_dict['services']:
            ret.services[x['name']] = eval(x['class']).from_dict(ret, x)  # TODO Use an internal dict
        for x in in_dict['links']:
            ret.links.append(eval(x['class']).from_dict(ret, x))  # TODO Use an internal dict
        x = in_dict['network_implementation']
        ret.network_implementation = eval(x['class']).from_dict(x)  # TODO Use an internal dict
        return ret

    def export_topo(self) -> str:
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def import_topo(cls, in_json: str) -> 'Topo':
        return Topo.from_dict(json.loads(in_json))

    @abstractmethod
    def create(self, *args, **params):
        pass

    def add_service(self, service: Service):
        if service.executor.name not in self.nodes:
            raise Exception(f"Node for service {service.name} was not added yet. Add nodes before services!")
        if service.name in self.services:
            raise Exception(f"Service with name {service.name} already exists")
        self.services[service.name] = service
        for intf in service.intfs:
            if intf.mac_address is None:
                intf.mac_address = self.mac_util.generate_new_mac()

    def get_service(self, name: str) -> Service:
        if name not in self.services:
            raise Exception(f"Service with name {name} does not exist")
        return self.services[name]

    def add_node(self, node: Node):
        if node.name in self.nodes:
            raise Exception(f"Node with name {node.name} already exists")
        self.nodes[node.name] = node
        for intf in node.intfs:
            if intf.mac_address is None:
                intf.mac_address = self.mac_util.generate_new_mac()

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
