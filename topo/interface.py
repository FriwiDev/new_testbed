from ipaddress import ip_address, ip_network


class Interface(object):
    name: str
    ips: list[ip_address] = []
    networks: list[ip_network] = []
    mac_address: str

    # name: str, mac_address: str = None
    def __init__(self, *args, **params):
        # Init from json when receiving dict
        if args and len(args) > 0 \
                and args[0] and isinstance(args[0], dict):
            self._init_from_dict(args[0])
            return
        # Init normally else
        # TODO Check presence and include hinted optional params above
        self.name = params['name']
        self.mac_address = params['mac_address'] if 'mac_address' in params else None

    def _init_from_dict(self, in_dict: dict):
        """Internal method to initialize from dictionary."""
        self.name = in_dict['name']
        for ip in in_dict['ips']:
            self.ips.append(ip_address(ip))
        for network in in_dict['networks']:
            self.networks.append(ip_network(network))
        self.mac_address = in_dict['mac_addr']

    def add_ip(self, ip: str, network: str) -> repr('Interface'):
        return self.add_ip(ip_address(ip), ip_network(network))

    def add_ip(self, ip: ip_address, network: ip_network) -> repr('Interface'):
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
            'mac_addr': self.mac_address
        }
