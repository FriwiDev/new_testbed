from abc import ABC, abstractmethod

from config.configuration import Command
from network.network_utils import NetworkUtils
from platform.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from topo.node import Node
from topo.service import Service, ServiceType


# TODO Needs file copy functionality as well
class NamespaceService(Service, ABC):
    def __init__(self, name: str, executor: Node, service_type: ServiceType):
        super().__init__(name, executor, service_type)

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only execute NamespaceService on a linux node")
        # Add namespace itself
        config.add_command(Command(f"ip netns add {self.name}"),
                           Command(f"ip netns del {self.name}"))
        # Connect namespace to bridge interfaces on host (pre created by the network topology)
        for dev in self.intfs:
            config.add_command(Command(f"ip link add {dev.bind_name}v0 type veth peer {dev.name} netns {self.name}"),
                               Command(f"ip link del {dev.bind_name}v0"))
            config.add_command(Command(f"brctl addif {dev.bind_name} {dev.bind_name}v0"),
                               Command(f"brctl delif {dev.bind_name} {dev.bind_name}v0"))
            NetworkUtils.set_mac(config, dev.name, dev.mac_address, self.ns_prefix())
            NetworkUtils.set_up(config, dev.bind_name + "v0")
            NetworkUtils.set_up(config, dev.bind_name)
            NetworkUtils.set_up(config, dev.name, self.ns_prefix())
        # Actual logic in the namespace will be provided by the implementation
        pass

    def ns_prefix(self) -> str:
        return f"ip netns exec {self.name} "
