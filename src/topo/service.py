import ipaddress
from abc import abstractmethod, ABC
from enum import Enum

from extensions.service_extension import ServiceExtension
from gui.gui_data_attachment import GuiDataAttachment
from topo.interface import Interface
from topo.node import Node
from topo.util import ClassUtil


class ServiceType(Enum):
    NONE, OVS, RYU = range(3)


class Service(ABC):
    def __init__(self, name: str, executor: Node, service_type: ServiceType = None):
        self.name = name
        self.type = service_type
        self.executor = executor
        self.intfs: list[Interface] = []
        self.extensions: dict[str, ServiceExtension] = {}
        self.gui_data: GuiDataAttachment = GuiDataAttachment()

    def configure(self, topo: 'Topo'):
        """To be implemented by services. Will execute when the topology is fully loaded."""
        pass

    def to_dict(self) -> dict:
        intfs = []
        for i in self.intfs:
            intfs.append(i.to_dict())
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'name': self.name,
            'executor': self.executor.name,
            'type': self.type.name,
            'intfs': [intf.to_dict() for intf in self.intfs],
            'service_extensions': [ext.to_dict() for ext in self.extensions.values()],
            'gui_data': self.gui_data.to_dict()
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Service':
        """Internal method to initialize from dictionary."""
        ret = cls(in_dict['name'],
                  topo.get_node(in_dict['executor']))
        for intf in in_dict['intfs']:
            ret.intfs.append(Interface.from_dict(intf))
        for ext in in_dict['service_extensions']:
            ret.extensions[ext['name']] = (ClassUtil.get_class_from_dict(ext).from_dict(topo, ext, ret))
        ret.gui_data = GuiDataAttachment.from_dict(in_dict['gui_data'])
        return ret

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        """Method to be implemented by every service definition"""
        pass

    @abstractmethod
    def append_to_configuration_enable(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
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

    def get_reachable_ips_via_for_other(self, intf: Interface) -> dict[ipaddress, int]:
        return self.get_reachable_ips_via_for_other_recursive(intf, [], 0)

    def get_reachable_ips_via_for_other_recursive(self, intf: Interface, visited: list['Service'], hops: int) -> \
            dict[ipaddress, int]:
        ret = {}
        for ip in intf.ips:
            if not ip.is_loopback:
                ret[ip] = hops
        if self in visited:
            return ret
        visited = visited.copy()
        visited.append(self)
        if self.is_switch():
            # Switches expose all other devices if calling instance is not a controller of this switch
            if intf.other_end_service is not None and intf.other_end_service not in self.controllers:
                for rintf in self.intfs:
                    if rintf.other_end_service not in self.controllers:
                        # Rintf is an interface that is not connected to a remote controller -> add it
                        for ip, h in rintf.other_end_service.get_reachable_ips_via_for_other_recursive(rintf.other_end,
                                                                                                       visited,
                                                                                                       hops + 1) \
                                .items():
                            if ip not in ret or ret[ip] > h:
                                ret[ip] = h
        return ret

    def get_reachable_ips_via(self, intf: Interface) -> dict[ipaddress, int]:
        if intf.other_end is None or intf.other_end_service is None:
            return {}
        reachable = intf.other_end_service.get_reachable_ips_via_for_other(intf.other_end)
        # Now iterate over all other interfaces and find if there is a shorter path via another way
        for other in self.intfs:
            if other != intf:
                if other.other_end_service:
                    other_reachable = other.other_end_service.get_reachable_ips_via_for_other(other.other_end)
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

    def build_routing_table(self) -> dict[ipaddress, ipaddress]:
        routing_table = {}
        routing_hops = {}
        # Add entries to table and replace with shorter options, if any
        for intf in self.intfs:
            entries = self.get_reachable_ips_via(intf)
            for ip, h in entries.items():
                if ip not in routing_table or routing_hops[ip] > h:
                    routing_table[ip] = intf.ips[0]
                    routing_hops[ip] = h
        # Delete local addresses from table
        to_del = []
        for ip, h in routing_table.items():
            if self.is_local_ip(ip):
                to_del.append(routing_table[ip])
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
