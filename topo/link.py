from topo.node import Node
from topo.service import Service
from topo.subnet import Subnet


class Link(object):
    gen = 0
    default_subnet = Subnet("10.0.0.0/16")

    def __init__(self, topo: 'Topo', service1: Service, service2: Service,
                 port1: int = None, port2: int = None,
                 intf_name1: str = None, intf_name2: str = None,
                 mac_addr1: str = None, mac_addr2: str = None,
                 subnet1: Subnet = None, subnet2: Subnet = None):
        self.service1 = service1
        self.service2 = service2
        # self.port1 = port1 if port1 else service1.executor.new_port(service1)  # TODO Why is there a port in our link?
        # self.port2 = port2 if port2 else service2.executor.new_port(service2)
        self.intf_name1 = intf_name1 if intf_name1 else Link.inf_name(service1.executor, self.__class__.gen)
        self.intf_name2 = intf_name2 if intf_name2 else Link.inf_name(service2.executor, self.__class__.gen + 1)
        self.__class__.gen += 2
        # Locate interfaces or add them
        if service1.get_interface(self.intf_name1):
            self.intf1 = service1.get_interface(self.intf_name1)
        else:
            self.intf1 = service1.add_interface_by_name(self.intf_name1)
            self.intf1.add_ip_from_subnet(subnet1 if subnet1 is not None else self.__class__.default_subnet)
        self.intf1.links.append(self)
        if service2.get_interface(self.intf_name2):
            self.intf2 = service2.get_interface(self.intf_name2)
        else:
            self.intf2 = service2.add_interface_by_name(self.intf_name2)
            self.intf2.add_ip_from_subnet(subnet1 if subnet1 is not None else self.__class__.default_subnet)
        self.intf2.links.append(self)
        # Apply mac addresses to devices, if any were provided
        if mac_addr1:
            self.intf1.mac_address = mac_addr1
        else:
            self.intf1.mac_address = topo.mac_util.generate_new_mac()
        if mac_addr2:
            self.intf2.mac_address = mac_addr2
        else:
            self.intf2.mac_address = topo.mac_util.generate_new_mac()
        self.intf1.other_end_service = self.service2
        self.intf2.other_end_service = self.service1
        self.intf1.other_end = self.intf2
        self.intf2.other_end = self.intf1

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'service1': self.service1.name,
            'service2': self.service2.name,
            'port1': self.port1,
            'port2': self.port2,
            'intf_name1': self.intf_name1,
            'intf_name2': self.intf_name2
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Link':
        """Internal method to initialize from dictionary."""
        ret = Link(
            topo.get_service(in_dict['service1']),
            topo.get_service(in_dict['service2']),
            in_dict['port1'],
            in_dict['port2'],
            in_dict['intf_name1'],
            in_dict['intf_name2'])
        return ret

    @classmethod
    def inf_name(cls, executor: Node, port1: int) -> str:
        return executor.name + "-eth" + str(port1)
