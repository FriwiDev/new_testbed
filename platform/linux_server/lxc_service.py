import os.path
from abc import ABC, abstractmethod
from os import PathLike

from config.configuration import Command
from network.network_utils import NetworkUtils
from platform.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from topo.node import Node
from topo.service import Service, ServiceType


class LXCService(Service, ABC):
    def __init__(self, name: str, executor: Node, service_type: ServiceType, image: str = "ubuntu", cpu: str = None, memory: str = None):
        super().__init__(name, executor, service_type)
        self.image = image
        self.cpu = cpu
        self.memory = memory
        self.files: list[(PathLike, str)] = []

    def add_file(self, local_file: PathLike, container_dir: str):
        if not container_dir.startswith("/"):
            raise Exception(f"Container path for copy to {self.name} is not absolute: {container_dir}")
        self.files.append((local_file, container_dir))

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only execute LXCService on a linux node")
        # Add container itself
        config.add_command(Command(f"lxc init {self.image} {self.name}"),
                           Command(f"lxc rm {self.name}"))
        if self.cpu:
            config.add_command(Command(f"lxc config set {self.name} limits.cpu {self.cpu}"),
                               Command())
        if self.memory:
            config.add_command(Command(f"lxc config set {self.name} limits.memory {self.cpu}"),
                               Command())
        # Copy files
        for file, path in self.files:
            # Make files available in configuration
            config.add_file(file)
            # Copy file to container
            config.add_command(self.file_copy(os.path.basename(file), path),
                               Command())
        # Start container
        config.add_command(Command(f"lxc start {self.name}"),
                           Command(f"lxc stop {self.name}"))
        # Connect container to bridge interfaces on host (pre created by the network topology)
        for dev in self.intfs:
            # Arguments in order:
            # 1: Bridge name on the host
            # 2: Container name
            # 3: lxc name for device
            # 4: Device name on the guest
            config.add_command(Command(f"lxc network attach {dev.bind_name} {self.name} {dev.name} {dev.name}"),
                               Command(f"lxc network detach {dev.bind_name} {self.name} {dev.name}"))
            NetworkUtils.set_up(config, dev.name, self.lxc_prefix())
            for i in range(len(dev.ips)):
                NetworkUtils.add_ip(config, dev.name, dev.ips[i], dev.networks[i], self.lxc_prefix())
        # Set up routes
        for ip, via in self.build_routing_table().items():
            NetworkUtils.add_route(config, ip, via, None, self.lxc_prefix())

        # Actual logic in the container will be provided by the implementation
        pass

    def lxc_prefix(self) -> str:
        return f"lxc exec {self.name} -- "

    def file_copy(self, local_file: str, container_dir: str) -> Command:
        if local_file.startswith("/"):
            raise Exception(f"Can not copy an absolute file path like {local_file} into container")
        if not container_dir.startswith("/"):
            raise Exception(f"Container path for copy to {self.name} is not absolute: {container_dir}")
        # Append / to prevent an avoidable error
        if not container_dir.endswith("/"):
            container_dir = container_dir + "/"
        return Command(f"lxc file push $(pwd)/{local_file} {self.name}{container_dir}")  # / is in container_dir


class SimpleLXCHost(LXCService):
    def __init__(self, name: str, executor: 'Node', cpu: str = None, memory: str = None):
        super().__init__(name, executor, ServiceType.NONE, "simple-host", cpu, memory)

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        super().append_to_configuration(config_builder, config)
        pass

    def is_switch(self) -> bool:
        return False

    def is_controller(self) -> bool:
        return False
