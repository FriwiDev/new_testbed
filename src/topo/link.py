from topo.node import Node
from topo.service import Service


class Link(object):
    # TODO Check and potentially add mac generation to serialized config

    def __init__(self, topo: 'Topo', service1: Service, service2: Service,
                 intf_name1: str = None, intf_name2: str = None,
                 mac_addr1: str = None, mac_addr2: str = None,
                 delay: int = 0, loss: float = 0,
                 delay_variation: int = 0, delay_correlation: float = 0,
                 loss_correlation: float = 0):
        """
        Values for loss and correlations always [0;1]
        """
        self.service1 = service1
        self.service2 = service2
        self.intf_name1 = intf_name1 if intf_name1 else Link.inf_name(service1.executor,
                                                                      service1.executor.get_new_virtual_device_num())
        self.intf_name2 = intf_name2 if intf_name2 else Link.inf_name(service2.executor,
                                                                      service2.executor.get_new_virtual_device_num())
        # Locate interfaces or add them
        if service1.get_interface(self.intf_name1):
            self.intf1 = service1.get_interface(self.intf_name1)
        else:
            self.intf1 = service1.add_interface_by_name(self.intf_name1)
            self.intf1.add_ip(
                topo.network_implementation.get_network_address_generator().generate_ip(service1, self.intf1),
                topo.network_implementation.get_network_address_generator().generate_network(service1, self.intf1)
            )
        self.intf1.links.append(self)
        if service2.get_interface(self.intf_name2):
            self.intf2 = service2.get_interface(self.intf_name2)
        else:
            self.intf2 = service2.add_interface_by_name(self.intf_name2)
            self.intf2.add_ip(
                topo.network_implementation.get_network_address_generator().generate_ip(service2, self.intf2),
                topo.network_implementation.get_network_address_generator().generate_network(service2, self.intf2)
            )
        self.intf2.links.append(self)
        # Apply mac addresses to devices, if any were provided
        if mac_addr1:
            self.intf1.mac_address = mac_addr1
        elif not self.intf1.mac_address:
            self.intf1.mac_address = topo.network_implementation.get_network_address_generator().generate_mac(service1,
                                                                                                              self.intf1)
        if mac_addr2:
            self.intf2.mac_address = mac_addr2
        elif not self.intf2.mac_address:
            self.intf2.mac_address = topo.network_implementation.get_network_address_generator().generate_mac(service2,
                                                                                                              self.intf2)
        self.intf1.other_end_service = self.service2
        self.intf2.other_end_service = self.service1
        self.intf1.other_end = self.intf2
        self.intf2.other_end = self.intf1
        self.delay = delay
        self.loss = loss
        self.delay_variation = delay_variation
        self.delay_correlation = delay_correlation
        self.loss_correlation = loss_correlation

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'service1': self.service1.name,
            'service2': self.service2.name,
            'intf_name1': self.intf_name1,
            'intf_name2': self.intf_name2,
            'delay': str(self.delay),
            'delay_variation': str(self.delay_variation),
            'delay_correlation': str(self.delay_correlation),
            'loss': str(self.loss),
            'loss_correlation': str(self.loss_correlation)
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Link':
        """Internal method to initialize from dictionary."""
        ret = Link(
            topo,
            topo.get_service(in_dict['service1']),
            topo.get_service(in_dict['service2']),
            in_dict['intf_name1'],
            in_dict['intf_name2'])
        ret.delay = int(in_dict['delay'])
        ret.delay_variation = int(in_dict['delay_variation'])
        ret.delay_correlation = float(in_dict['delay_correlation'])
        ret.loss = float(in_dict['loss'])
        ret.loss_correlation = float(in_dict['loss_correlation'])
        return ret

    @classmethod
    def inf_name(cls, executor: Node, port1: int) -> str:
        return executor.name + "-eth" + str(port1)