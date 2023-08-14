import typing
from abc import ABC, abstractmethod
from os import PathLike
from pathlib import PurePath, Path

from config.configuration import Command
from network.network_utils import NetworkUtils
from platforms.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from topo.node import Node
from topo.service import Service, ServiceType


class LXCService(Service, ABC):
    """A service residing in a lcx container."""

    def __init__(self, name: str, executor: Node, service_type: ServiceType, late_init: bool = False, image: str = "ubuntu", cpu: str = None,
                 cpu_allowance: str = None, memory: str = None):
        """name: name for service
           executor: node this service is running on
           service_type: the type of this service for easier identification
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)"""
        super().__init__(name, executor, service_type, late_init)
        self.image = image
        self.cpu = cpu
        self.cpu_allowance = cpu_allowance
        self.memory = memory
        self.files: typing.List[(PathLike, PathLike)] = []

    def add_file(self, local_file: PathLike, container_dir: PathLike):
        if not str(container_dir).startswith("/"):
            raise Exception(f"Container path for copy to {self.name} is not absolute: {container_dir}")
        self.files.append((local_file, container_dir))

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only execute LXCService on a linux node")
        # Add container itself
        if create:
            config.add_command(Command(f"lxc init {self.image} {self.name}"),
                               Command(f"lxc rm {self.name}"))
            if self.cpu:
                config.add_command(Command(f"lxc config set {self.name} limits.cpu {self.cpu}"),
                                   Command())
            if self.cpu_allowance:
                config.add_command(Command(f"lxc config set {self.name} limits.cpu.allowance {self.cpu_allowance}"),
                                   Command())
            if self.memory:
                config.add_command(Command(f"lxc config set {self.name} limits.memory {self.memory}"),
                                   Command())

            # Copy files
            for file, path in self.files:
                # Make files available in configuration
                config.add_file(self, file, path)

        # Insert file copy placeholder
        config.add_command(Command(f"#filecopybeforelaunch {self.name}"),
                           Command())

        if create:
            # Set up early
            for ext in self.extensions.values():
                ext.append_to_configuration_pre_start(self.lxc_prefix(), config_builder, config)

        # Start container
        config.add_command(Command(f"lxc start {self.name}"),
                           Command(f"lxc stop {self.name}"))

        # Insert file copy placeholder
        config.add_command(Command(f"#filecopyafterlaunch {self.name}"),
                           Command())

        intf_blacklist = []
        for ext in self.extensions.values():
            for i in ext.claimed_interfaces:
                intf_blacklist.append(i)

        # Connect container to bridge interfaces on host (pre created by the network topology)
        for dev in self.intfs:
            # Arguments in order:
            # 1: Bridge name on the host
            # 2: Container name
            # 3: lxc name for device
            # 4: Device name on the guest
            if dev.name not in intf_blacklist:
                if create:
                    config.add_command(Command(f"lxc network attach {dev.bind_name} {self.name} {dev.name} {dev.name}"),
                                       Command(f"lxc network detach {dev.bind_name} {self.name} {dev.name}"))
                NetworkUtils.set_mac(config, dev.name, dev.mac_address, self.lxc_prefix())
                NetworkUtils.set_up(config, dev.name, self.lxc_prefix())
                for i in range(len(dev.ips)):
                    NetworkUtils.add_ip(config, dev.name, dev.ips[i], dev.networks[i], self.lxc_prefix())
        # Set up routes
        # For switch it is with only links to controllers and excluded devices
        for ip, via in self.build_routing_table(for_switch=self.is_switch()).items():
            NetworkUtils.add_route(config, ip, None, None, via, self.lxc_prefix())

        # Set up extensions
        for ext in self.extensions.values():
            ext.append_to_configuration(self.lxc_prefix(), config_builder, config)

        # Actual logic in the container will be provided by the implementation
        pass

    def lxc_prefix(self) -> str:
        return f"lxc exec {self.name} -- "

    def command_prefix(self) -> str:
        return self.lxc_prefix()

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(LXCService, self).to_dict(without_gui), **{
            'image': self.image,
            'cpu': self.cpu,
            'memory': self.memory,
            'files': [{'path': str(PurePath(x)), 'to': str(y)} for x, y in self.files],
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'LXCService':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.image = in_dict['image']
        ret.cpu = in_dict['cpu']
        ret.memory = in_dict['memory']
        ret.files = [(Path(x['path']), Path(x['to'])) for x in in_dict['files']]
        return ret


class SimpleLXCHost(LXCService):
    def __init__(self, name: str, executor: 'Node', late_init: bool = False, cpu: str = None, cpu_allowance: str = None, memory: str = None,
                 image: str = "simple-host"):
        super().__init__(name, executor, ServiceType.NONE, late_init, image, cpu, cpu_allowance, memory)

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        pass

    def is_switch(self) -> bool:
        return False

    def is_controller(self) -> bool:
        return False
