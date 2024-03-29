import ipaddress
import typing
from abc import abstractmethod, ABC
from enum import Enum
from typing import Dict

from extensions.service_extension import ServiceExtension
from gui.gui_data_attachment import GuiDataAttachment
from topo.interface import Interface
from topo.node import Node
from topo.util import ClassUtil


class ServiceType(Enum):
    NONE, OVS, RYU, DSMF, ESMF = range(5)


class Service(ABC):
    """A service running on a node."""

    def __init__(self, name: str, executor: Node, service_type: ServiceType = None, late_init: bool = False):
        """name: name for service
           executor: node this service is running on
           service_type: the type of this service for easier identification"""
        self.name = name
        self.type = service_type
        self.executor = executor
        self.late_init = late_init
        self.intfs: typing.List[Interface] = []
        self.main_ip: ipaddress or None = None
        self.main_network: ipaddress or None = None
        self.extensions: Dict[str, ServiceExtension] = {}
        self.gui_data: GuiDataAttachment = GuiDataAttachment()

    def configure(self, topo: 'Topo'):
        """To be implemented by services. Will execute when the topology is fully loaded."""
        pass

    def to_dict(self, without_gui: bool = False) -> dict:
        intfs = []
        for i in self.intfs:
            intfs.append(i.to_dict())
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'name': self.name,
            'executor': self.executor.name,
            'type': self.type.name,
            'main_ip': str(self.main_ip),
            'main_network': str(self.main_network),
            'intfs': [intf.to_dict(without_gui) for intf in self.intfs],
            'service_extensions': [ext.to_dict() for ext in self.extensions.values()],
            'gui_data': None if without_gui else self.gui_data.to_dict()
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Service':
        """Internal method to initialize from dictionary."""
        ret = cls(in_dict['name'],
                  topo.get_node(in_dict['executor']),
                  late_init=True)
        for intf in in_dict['intfs']:
            ret.intfs.append(Interface.from_dict(intf))
        for ext in in_dict['service_extensions']:
            ret.extensions[ext['name']] = (ClassUtil.get_class_from_dict(ext).from_dict(topo, ext, ret))
        ret.gui_data = GuiDataAttachment.from_dict(in_dict['gui_data'])
        ret.main_ip = ipaddress.ip_address(in_dict['main_ip'])
        ret.main_network = ipaddress.ip_network(in_dict['main_network'])
        return ret

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        """Method to be implemented by every service definition"""
        pass

    def get_interface(self, intf_name: str) -> Interface:
        for i in self.intfs:
            if i.name == intf_name:
                return i
        return None

    def remove_interface(self, intf: str) -> Interface:
        found = None
        for i in self.intfs:
            if i.name == intf:
                found = i
                break
        if found:
            self.intfs.remove(found)
        return found

    def add_interface(self, intf: Interface) -> 'Service':
        for i in self.intfs:
            if i.name == intf:
                raise Exception(f"Interface with name {intf.name} already exists in service {self.name}")
        self.intfs.append(intf)
        return self

    def add_interface_by_name(self, intf_name: str) -> Interface:
        i = Interface(intf_name)
        self.add_interface(i)
        return i

    @abstractmethod
    def is_switch(self) -> bool:
        pass

    @abstractmethod
    def is_controller(self) -> bool:
        pass

    def command_prefix(self) -> str:
        return ""

    def get_valid_ip_for(self, other: 'Service') -> ipaddress or None:
        routing_table = other.build_routing_table()
        for ip, via in routing_table.items():
            if self.has_ip(ip):
                return ip
        return None

    def get_reachable_ips_via_for_other(self, intf: Interface, for_switch: bool = False) -> Dict[ipaddress.ip_address, int]:
        return self.get_reachable_ips_via_for_other_recursive(intf, [], 0, for_switch)

    def get_reachable_ips_via_for_other_recursive(self, intf: Interface, visited: typing.List['Service'], hops: int,
                                                  for_switch: bool = False) -> Dict[ipaddress.ip_address, int]:
        ret = {}
        if not for_switch or self.is_controller():
            for ip in intf.ips:
                if not ip.is_loopback:
                    ret[ip] = hops
        if self in visited:
            return ret
        visited = visited.copy()
        visited.append(self)
        if self.is_switch():
            # Switches expose all other devices if calling instance is not a controller of or excluded from this switch
            if intf.other_end_service is not None and intf.other_end_service not in self.controllers\
                    and not self.is_switch_exclude(intf):
                for rintf in self.intfs:
                    if rintf.other_end_service not in self.controllers and not self.is_switch_exclude(rintf):
                        # Rintf is an interface that is not connected to a remote controller -> add it
                        for ip, h in rintf.other_end_service.get_reachable_ips_via_for_other_recursive(rintf.other_end,
                                                                                                       visited,
                                                                                                       hops + 1,
                                                                                                       for_switch) \
                                .items():
                            if ip not in ret or ret[ip] > h:
                                ret[ip] = h
                for x in self.gateway_to_subnets:
                    ret[x] = 1
        return ret

    def get_reachable_ips_via(self, intf: Interface, for_switch: bool = False) -> Dict[ipaddress.ip_address, int]:
        if intf.other_end is None or intf.other_end_service is None:
            return {}
        reachable = intf.other_end_service.get_reachable_ips_via_for_other(intf.other_end, for_switch)
        # Now iterate over all other interfaces and find if there is a shorter path via another way
        for other in self.intfs:
            if other != intf:
                if other.other_end_service:
                    other_reachable = other.other_end_service.get_reachable_ips_via_for_other(other.other_end, for_switch)
                    for ip, h in other_reachable.items():
                        if ip in reachable and reachable[ip] > h:
                            # There is a better way to reach the desired ip
                            del reachable[ip]
        return reachable

    def is_local_ip(self, ip: ipaddress) -> bool:
        if ip.is_loopback:
            return True
        for intf in self.intfs:
            if ip in intf.ips:
                return True
        return False

    def build_routing_table(self, with_tunnel: bool = False, for_switch: bool = False) -> Dict[ipaddress.ip_address, Interface]:
        routing_table = {}
        routing_hops = {}
        # Add entries to table and replace with shorter options, if any
        for intf in self.intfs:
            if not self.is_switch() or intf.other_end_service in self.controllers or self.is_switch_exclude(intf):
                if with_tunnel or not intf.is_tunnel:
                    entries = self.get_reachable_ips_via(intf, False)
                    for ip, h in entries.items():
                        if ip not in routing_table or routing_hops[ip] > h:
                            routing_table[ip] = intf
                            routing_hops[ip] = h
        # Delete local addresses from table
        to_del = []
        for ip, h in routing_table.items():
            if self.is_local_ip(ip):
                to_del.append(ip)
        for del_ip in to_del:
            del routing_table[del_ip]
        # Return final table
        return routing_table

    def has_ip(self, ip: ipaddress) -> bool:
        for intf in self.intfs:
            if ip in intf.ips:
                return True
        return False

    def add_extension(self, ext: 'ServiceExtension'):
        if ext.name in self.extensions:
            raise Exception("Service extension with name " + ext.name + " already exists in service " + self.name)
        self.extensions[ext.name] = ext
