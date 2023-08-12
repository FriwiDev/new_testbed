import ipaddress
from abc import ABC
from ipaddress import ip_address, ip_network

from config.configuration import Command


class NetworkUtils(ABC):
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
    def set_mac(cls, config: 'Configuration', device_name: str, mac_address: str, prefix: str = None):
        if prefix is None:
            prefix = ''
        else:
            prefix += ' '
        config.add_command(Command(f"{prefix}ip link set dev {device_name} address {mac_address}"),
                           Command())
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
    def add_route(cls, config: 'Configuration', ip: ipaddress, via_ip: ip_address, via_network: ip_network = None,
                  via_dev: 'Interface' or None = None, prefix: str = None):
        if ip.is_loopback or (via_ip is not None and via_ip.is_loopback):
            pass
        if prefix is None:
            prefix = ''
        else:
            prefix += ' '
        if via_network is not None:
            config.add_command(
                Command(f"{prefix}ip route add {str(ip)} via {str(via_ip)}/{str(via_network.prefixlen)}"),
                Command(f"{prefix}ip route del {str(ip)}"))
        elif via_dev is not None:
            config.add_command(
                Command(f"{prefix}ip route add {str(ip)} dev {str(via_dev.name)}"),
                Command(f"{prefix}ip route del {str(ip)}"))
        else:
            config.add_command(Command(f"{prefix}ip route add {str(ip)} via {str(via_ip)}"),
                               Command(f"{prefix}ip route del {str(ip)}"))
        pass

    @classmethod
    def add_qdisc(cls, config: 'Configuration', dev_name: str, delay: int, loss: float,
                  delay_variation: int = 0, delay_correlation: float = 0, loss_correlation: float = 0,
                  bandwidth: int = 0, burst: int = 0,
                  prefix: str = None):
        if prefix is None:
            prefix = ''
        else:
            prefix += ' '

        if delay > 0 or loss > 0:
            cmd = f"{prefix}tc qdisc add dev {dev_name} root handle 1: netem"
            if delay > 0:
                cmd += f" delay {delay}"
                if delay_variation > 0:
                    cmd += f" {delay_variation}"
                    if delay_correlation > 0:
                        cmd += f" {delay_correlation * 100}%"
            if loss > 0:
                cmd += f" loss {loss * 100}%"
                if loss_correlation > 0:
                    cmd += f" {loss_correlation * 100}%"

            config.add_command(
                Command(cmd),
                Command(f"{prefix}tc qdisc delete dev {dev_name} root netem || true")
            )

            if bandwidth > 0:
                if burst == 0:
                    burst = bandwidth / 10
                config.add_command(
                    Command(f"{prefix}tc qdisc add dev {dev_name} parent 1: handle 2: tbf rate {bandwidth} burst {int(burst/8)} "
                            f"limit {int(burst/8)}"),
                    Command(f"{prefix}tc qdisc delete dev {dev_name} parent 1: handle 2 || true")
                )
        else:
            if bandwidth > 0:
                if burst == 0:
                    burst = bandwidth * 1.25
                config.add_command(
                    Command(f"{prefix}tc qdisc add dev {dev_name} root tbf rate {bandwidth} burst {int(burst/8)} "
                            f"limit {int(burst/8)}"),
                    Command(f"{prefix}tc qdisc delete dev {dev_name} root tbf || true")
                )

    @classmethod
    def format_bytes(cls, bytes: float) -> str:
        suffix = ""
        if bytes > 1024:
            bytes /= 1024
            suffix = "K"
        if bytes > 1024:
            bytes /= 1024
            suffix = "M"
        if bytes > 1024:
            bytes /= 1024
            suffix = "G"
        if bytes > 1024:
            bytes /= 1024
            suffix = "T"
        return format(bytes, '.1f') + " " + suffix

    @classmethod
    def format_thousands(cls, bytes: float) -> str:
        suffix = ""
        if bytes > 1000:
            bytes /= 1000
            suffix = "K"
        if bytes > 1000:
            bytes /= 1000
            suffix = "M"
        if bytes > 1000:
            bytes /= 1000
            suffix = "G"
        if bytes > 1000:
            bytes /= 1000
            suffix = "T"
        return format(bytes, '.1f') + " " + suffix
