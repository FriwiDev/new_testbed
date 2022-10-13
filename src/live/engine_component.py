from abc import ABC, abstractmethod
from enum import Enum
from ipaddress import ip_network, ip_address

from extensions.macvlan_extension import MacVlanServiceExtension
from extensions.wireguard_extension import WireguardServiceExtension
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
    def create(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def remove(self):
        pass

    @abstractmethod
    def get_status(self) -> EngineComponentStatus:
        pass


class EngineInterface(EngineComponent):
    def __init__(self, engine: 'Engine', component: Interface, parent: 'EngineNode' or 'EngineService'):
        super().__init__(engine, component)
        self.extension = None
        self.parent = parent
        self.live_ips: list[(ip_address, ip_network)] = []
        self.live_mac: str or None = None
        self.interface_state: EngineInterfaceState = EngineInterfaceState.UNKNOWN
        self.ifstat: (int, int) or None = None

    def create(self):
        raise Exception("Creating is unsupported on interface components")

    def start(self):
        pass

    def stop(self):
        pass

    def remove(self):
        raise Exception("Removing is unsupported on interface components")

    def get_status(self) -> EngineComponentStatus:
        pass


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

    def create(self):
        raise Exception("Creating is unsupported on service components")

    def start(self):
        pass

    def stop(self):
        pass

    def remove(self):
        raise Exception("Removing is unsupported on service components")

    def get_status(self) -> EngineComponentStatus:
        pass


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

    def create(self):
        raise Exception("Creating is unsupported on node components")

    def start(self):
        pass

    def stop(self):
        pass

    def remove(self):
        raise Exception("Removing is unsupported on node components")

    def get_status(self) -> EngineComponentStatus:
        pass
