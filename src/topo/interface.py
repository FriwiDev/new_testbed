from ipaddress import ip_address, ip_network


class Interface(object):
    def __init__(self, name: str, mac_address: str = None):
        self.name = name
        self.mac_address = mac_address
        self.ips: list[ip_address] = []
        self.networks: list[ip_network] = []
        self.links: list['Link'] = []
        self.bind_name = None  # Used by network topologies to cache bridge names
        self.other_end_service = None
        self.other_end = None

    def add_ip(self, ip: str or ip_address, network: str or ip_network) -> 'Interface':
        if isinstance(ip, str):
            ip = ip_address(ip)
        if isinstance(network, str):
            network = ip_network(network)
        self.ips.append(ip)
        self.networks.append(network)
        return self

    def to_dict(self) -> dict:
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
            'bind_name': self.bind_name
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
        return ret