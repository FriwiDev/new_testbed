import ipaddress
from enum import Enum
from typing import Dict

from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class InterfaceState(Enum):
    UNKNOWN, UP, DOWN = range(3)


class IpAddrSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Service or Node):
        super().__init__(target.executor if isinstance(target, Service) else target,
                         (target.command_prefix() if isinstance(target, Service) else "") + "ip addr")
        self.add_consumer(self)
        self.results: Dict[int, (str, InterfaceState, str, [(ipaddress.ip_address, ipaddress.ip_network)])] = {}
        self.current_interface: None or (int, str, InterfaceState, str, [(ipaddress.ip_address, ipaddress.ip_network)]) \
            = None

    def on_out(self, output: str):
        if output.split(":")[0].isdigit():
            if self.current_interface:
                ind, name, state, mac, li = self.current_interface
                self.results[ind] = (name, state, mac, li)
            name = output.split(" ")[1].split("@")[0].removesuffix(":")
            state = InterfaceState.UNKNOWN
            for s in output.split(" "):
                if s == "UNKNOWN" or s == "DOWN" or s == "UP":
                    state = InterfaceState[s]
            self.current_interface = (int(output.split(":")[0]), name, state, None, [])
            return

        output = output.strip()
        if output.startswith("link") and not output.startswith("link/none"):
            ind, name, state, _, li = self.current_interface
            mac = output.split(" ")[1]
            self.current_interface = (ind, name, state, mac, li)
        elif output.startswith("inet6"):
            ip_str = output.split(" ")[1]
            prefix_len = int(ip_str.split("/")[1])
            ip = ipaddress.IPv6Address(ip_str.split("/")[0])
            network_prefix = (int(ip) >> prefix_len) << prefix_len
            ip_network = ipaddress.IPv6Network(str(ipaddress.IPv6Address(network_prefix)) + "/" + str(prefix_len))
            self.current_interface[4].append((ip, ip_network))
        elif output.startswith("inet"):
            ip_str = output.split(" ")[1]
            prefix_len = int(ip_str.split("/")[1])
            ip = ipaddress.ip_address(ip_str.split("/")[0])
            network_prefix = (int(ip) >> prefix_len) << prefix_len
            ip_network = ipaddress.ip_network(str(ipaddress.ip_address(network_prefix)) + "/" + str(prefix_len))
            self.current_interface[4].append((ip, ip_network))
        pass

    def on_return(self, code: int):
        if self.current_interface:
            ind, name, state, mac, li = self.current_interface
            self.results[ind] = (name, state, mac, li)
            self.current_interface = None
        pass
