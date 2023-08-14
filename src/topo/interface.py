from ipaddress import ip_address, ip_network

from gui.gui_data_attachment import GuiDataAttachment


class Interface(object):
    """An interface of a node or service."""

    def __init__(self, name: str, mac_address: str = None):
        """name: The name of the interface
           mac_address: The mac address of the interface"""
        self.name = name
        self.mac_address = mac_address
        self.ips: typing.List[ip_address] = []
        self.networks: typing.List[ip_network] = []
        self.links: typing.List['Link'] = []
        self.bind_name = None  # Used by network topologies to cache bridge names
        self.other_end_service = None
        self.other_end = None
        self.gui_data: GuiDataAttachment = GuiDataAttachment()
        self.is_tunnel = False

    def add_ip(self, ip: str or ip_address, network: str or ip_network) -> 'Interface':
        if isinstance(ip, str):
            ip = ip_address(ip)
        if isinstance(network, str):
            network = ip_network(network)
        self.ips.append(ip)
        self.networks.append(network)
        return self

    def to_dict(self, without_gui: bool = False) -> dict:
        ip_str = []
        for ip in self.ips:
            ip_str.append(format(ip))
        network_str = []
        for network in self.networks:
            network_str.append(format(network))
        return {
            'name': self.name,
            'ips': ip_str,
            'networks': network_str,
            'mac_addr': self.mac_address,
            'bind_name': self.bind_name,
            'gui_data': None if without_gui else self.gui_data.to_dict()
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Interface':
        """Internal method to initialize from dictionary."""
        name = in_dict['name']
        mac_address = in_dict['mac_addr']
        ret = Interface(name, mac_address)
        for ip in in_dict['ips']:
            ret.ips.append(ip_address(ip))
        for network in in_dict['networks']:
            ret.networks.append(ip_network(network))
        ret.bind_name = in_dict['bind_name']
        ret.gui_data = GuiDataAttachment.from_dict(in_dict['gui_data'])
        return ret
