from topo.node import Node


class Link(object):
    # service1: Service, service2: Service,
    # port1: int = None, port2: int = None,
    # intf_name1: str = None, intf_name2: str = None,
    # mac_addr1: str = None, mac_addr2: str = None,
    def __init__(self, *args, **params):
        # Init from json when receiving dict
        if args and len(args) > 1 \
                and args[0] \
                and args[1] and isinstance(args[1], dict):
            self._init_from_dict(args[0], args[1])
            return
        # Init normally else
        # TODO Check presence and include hinted optional params above
        service1 = params['service1'] if 'service1' in params else None
        service2 = params['service2'] if 'service2' in params else None
        port1 = params['port1'] if 'port1' in params else None
        port2 = params['port2'] if 'port2' in params else None
        intf_name1 = params['intf_name1'] if 'intf_name1' in params else None
        intf_name2 = params['intf_name2'] if 'intf_name2' in params else None
        mac_addr1 = params['mac_addr1'] if 'mac_addr1' in params else None
        mac_addr2 = params['mac_addr2'] if 'mac_addr2' in params else None
        self.service1 = service1
        self.service2 = service2
        self.port1 = port1 if port1 else service1.executor.new_port()
        self.port2 = port2 if port2 else service1.executor.new_port()
        self.intf_name1 = intf_name1 if intf_name1 else Link.inf_name(service1.executor, port1)
        self.intf_name2 = intf_name2 if intf_name2 else Link.inf_name(service2.executor, port2)
        self.mac_addr1 = mac_addr1  # TODO default initialization
        self.mac_addr2 = mac_addr2
        self.params = params

    def _init_from_dict(self, topo: 'Topo', in_dict: dict):
        """Internal method to initialize from dictionary."""
        self.service1 = topo.get_service(in_dict['service1'])
        self.service2 = topo.get_service(in_dict['service2'])
        self.port1 = in_dict['port1']
        self.port2 = in_dict['port2']
        self.intf_name1 = in_dict['intf_name1']
        self.intf_name2 = in_dict['intf_name2']
        self.mac_addr1 = in_dict['mac_addr1']
        self.mac_addr2 = in_dict['mac_addr2']
        self.params = in_dict['params']

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'service1': self.service1.name,
            'service2': self.service2.name,
            'port1': self.port1,
            'port2': self.port2,
            'intf_name1': self.intf_name1,
            'intf_name2': self.intf_name2,
            'mac_addr1': self.mac_addr1,
            'mac_addr2': self.mac_addr2#,
            #'params': self.params
        }

    @classmethod
    def inf_name(self, executor: Node, port1: int):
        return executor.name + "-eth" + str(port1)
