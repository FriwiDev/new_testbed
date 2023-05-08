import ipaddress
from abc import ABC, abstractmethod
from enum import Enum
from ipaddress import ip_network, ip_address

from extensions.macvlan_extension import MacVlanServiceExtension
from extensions.wireguard_extension import WireguardServiceExtension
from live.engine_component import EngineService
from ssh.lock_read_command import LockReadSSHCommand
from ssh.output_consumer import PrintOutputConsumer
from ssh.ssh_command import SSHCommand
from topo.interface import Interface
from topo.node import Node
from topo.service import Service
from topo.topo import Topo


class EngineComponentStatus(Enum):
    UNREACHABLE, REMOVED, RUNNING, STOPPED = range(4)


class EngineInterfaceState(Enum):
    UNKNOWN, UP, DOWN = range(3)


class EngineComponent(ABC):
    def __init__(self, engine: 'Engine', component: Interface or Service or Node):
        self.engine = engine
        self.component = component
        self.status = EngineComponentStatus.UNREACHABLE

    @abstractmethod
    def get_name(self) -> str:
        pass

    def __str__(self):
        return self.get_name()


class EngineInterface(EngineComponent):

    def __init__(self, engine: 'Engine', component: Interface, parent: 'EngineNode' or 'EngineService'):
        super().__init__(engine, component)
        self.extension = None
        self.parent = parent
        self.live_ips: list[(ip_address, ip_network)] = []
        self.live_mac: str or None = None
        self.interface_state: EngineInterfaceState = EngineInterfaceState.UNKNOWN
        self.ifstat: (int, int) or None = None
        self.tcqdisc: (int, int, float, float, float) = (0, 0, 0, 0, 0)

    def get_name(self) -> str:
        return f"{self.component.name}@{self.parent.component.name}"


class EngineService(EngineComponent):
    def __init__(self, engine: 'Engine', component: Service, parent: 'EngineNode'):
        super().__init__(engine, component)
        self.parent = parent
        self.intfs: dict[str, EngineInterface] = {}
        for intf in component.intfs:
            self.intfs[intf.name] = EngineInterface(engine, intf, self)
        for ext in component.extensions.values():
            if isinstance(ext, WireguardServiceExtension):
                self.intfs[ext.dev_name].extension = ext
            elif isinstance(ext, MacVlanServiceExtension):
                self.intfs["eth0"].extension = ext

    def get_name(self) -> str:
        return f"{self.component.name}"

    def get_reachable_ip_from_other_by_subnet(self, other: EngineService) -> ipaddress.ip_address or None:
        for intf in other.intfs.values():
            for _, subnet in intf.live_ips:
                for intf_local in self.intfs.values():
                    for ip_local, subnet_local in intf_local.live_ips:
                        if subnet_local == subnet:
                            return ip_local
        return None

    def cmd(self, cmd: str):
        cmd = SSHCommand(self.parent.component, self.component.command_prefix() + cmd)
        cmd.run()

    def cmd_print(self, cmd: str):
        cmd = SSHCommand(self.parent.component, self.component.command_prefix() + cmd)
        cmd.add_consumer(PrintOutputConsumer())
        cmd.run()

class EngineNode(EngineComponent):
    def __init__(self, engine: 'Engine', component: Node, topo: Topo):
        super().__init__(engine, component)
        self.services: dict[str, EngineService] = {}
        for service in topo.services.values():
            if service.executor == component:
                self.services[service.name] = EngineService(engine, service, self)
        self.intfs: dict[str, EngineInterface] = {}
        for intf in component.intfs:
            self.intfs[intf.name] = EngineInterface(engine, intf, self)

    def get_name(self) -> str:
        return f"{self.component.name}"

    def read_topology(self) -> Topo or None:
        cmd = LockReadSSHCommand(self.component, "/tmp", "current_topology.json")
        cmd.run()
        if cmd.content == "":
            return None
        else:
            return Topo.import_topo(cmd.content)

    def cmd(self, cmd: str):
        cmd = SSHCommand(self.component, cmd)
        cmd.run()

    def cmd_print(self, cmd: str):
        cmd = SSHCommand(self.component, cmd)
        cmd.add_consumer(PrintOutputConsumer())
        cmd.run()
