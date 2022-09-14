import json
from abc import abstractmethod

from network.vxlan_network import VxLanNetworkImplementation
from topo.link import Link
from topo.node import Node
from topo.service import Service
from topo.util import MacUtil, ClassUtil


class Topo(object):
    def __init__(self, nodes=None,
                 links=None,
                 services=None,
                 network_implementation: 'NetworkImplementation' = None,
                 *args, **params):
        if nodes is None:
            nodes = {}
        if links is None:
            links = []
        if services is None:
            services = {}
        if network_implementation is None:
            network_implementation = VxLanNetworkImplementation("10.0.0.0/24", "239.1.1.1")  # TODO Add better default
        self.mac_util = MacUtil()
        self.nodes = nodes
        self.links = links
        self.services = services
        self.network_implementation = network_implementation
        self.network_implementation.inject_topology(self)
        self.create(args, params)
        self.network_implementation.configure()
        for service in self.services.values():
            service.configure(self)

    def to_dict(self) -> dict:
        nodes = []
        for n in self.nodes:
            nodes.append(self.nodes[n].to_dict())
        services = []
        for s in self.services:
            services.append(self.services[s].to_dict())
        links = []
        for link in self.links:
            links.append(link.to_dict())
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
            ret.nodes[x['name']] = ClassUtil.get_class_from_dict(x).from_dict(x)
        for x in in_dict['services']:
            ret.services[x['name']] = ClassUtil.get_class_from_dict(x).from_dict(ret, x)
        for x in in_dict['links']:
            ret.links.append(ClassUtil.get_class_from_dict(x).from_dict(ret, x))
        x = in_dict['network_implementation']
        ret.network_implementation = ClassUtil.get_class_from_dict(x).from_dict(x)
        ret.network_implementation.inject_topology(ret)
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
                intf.mac_address = self.network_implementation.get_network_address_generator().generate_mac(service,
                                                                                                            intf)

    def get_service(self, name: str) -> Service:
        if name not in self.services:
            raise Exception(f"Service with name {name} does not exist")
        return self.services[name]

    def add_node(self, node: Node):
        if node.name in self.nodes:
            raise Exception(f"Node with name {node.name} already exists")
        self.nodes[node.name] = node
        # We do not determine the mac addresses for real hardware (at least not for now)
        # for intf in node.intfs:
        #    if intf.mac_address is None:
        #        intf.mac_address = self.mac_util.generate_new_mac()

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


class TopoUtil(object):
    @classmethod
    def from_file(cls, file_path: str) -> Topo:
        # No error handling, but user should be able to understand
        file = open(file_path, "r")
        ret = file.read()
        file.close()
        return Topo.import_topo(ret)

    @classmethod
    def to_file(cls, file_path: str, topo: Topo):
        ret = topo.export_topo()
        # No error handling, but user should be able to understand
        file = open(file_path, "w")
        file.write(ret)
        file.close()
