from abc import ABC, abstractmethod

from topo.node import Node
from topo.service import Service
from topo.topo import Topo


class EngineTopologyChangeListener(ABC):
    @abstractmethod
    def on_topology_change(self, old_topo: Topo, new_topo: Topo):
        pass

    @abstractmethod
    def on_component_change(self, old_component: Service or Node or None, new_component: Service or Node or None):
        pass
