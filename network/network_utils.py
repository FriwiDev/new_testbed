from ipaddress import ip_address, ip_network

from config.configuration import Command


class NetworkUtils(object):
    @classmethod
    def set_up(cls, config: 'Configuration', device_name: str, prefix: str = None):
        if prefix is None:
            prefix = ''
        else:
            prefix += ' '
        config.add_command(Command(f"{prefix}ip link set dev {device_name} up"),
                           Command(f"{prefix}ip link set dev {device_name} down"))
        pass

    @classmethod
    def add_ip(cls, config: 'Configuration', device_name: str, ip: ip_address, network: ip_network, prefix: str = None):
        if prefix is None:
            prefix = ''
        else:
            prefix += ' '
        config.add_command(Command(f"{prefix}ip addr add dev {device_name} {str(ip)}/{str(network.prefixlen)}"),
                           Command(f"{prefix}ip addr del dev {device_name} {str(ip)}/{str(network.prefixlen)}"))
        pass

    @classmethod
    def add_route(cls, config: 'Configuration', ip: ip_address, via_ip: ip_address, via_network: ip_network = None,
                  prefix: str = None):
        if ip.is_loopback or via_ip.is_loopback:
            pass
        if prefix is None:
            prefix = ''
        else:
            prefix += ' '
        if via_network is None:
            config.add_command(Command(f"{prefix}ip route add {str(ip)} via {str(via_ip)}"),
                               Command(f"{prefix}ip route del {str(ip)}"))
        else:
            config.add_command(
                Command(f"{prefix}ip route add {str(ip)} via {str(via_ip)}/{str(via_network.prefixlen)}"),
                Command(f"{prefix}ip route del {str(ip)}"))
        pass
