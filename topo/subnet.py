from ipaddress import ip_network, ip_address


class Subnet(object):
    def __init__(self, network: ip_network or str):
        if isinstance(network, str):
            network = ip_network(network)
        self.network = network
        self.current_index = 2

    def generate_next_ip(self) -> ip_address:
        ret = ip_address(int(self.network.network_address) + self.current_index)
        self.current_index += 1
        return ret
