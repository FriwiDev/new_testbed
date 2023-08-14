import os
import pathlib
from abc import ABC, abstractmethod

from config.configuration import Command
from platforms.linux_server.lxc_service import LXCService
from ssh.localcommand import LocalCommand
from topo.node import Node
from topo.service import ServiceType


class TestbedService(LXCService, ABC):
    """A service able to interact with the testbed in a lcx container."""

    def __init__(self, name: str, executor: Node, service_type: ServiceType, image: str = "ryu", cpu: str = None,
                 cpu_allowance: str = None, memory: str = None, key_dir: str = "../ssh_keys", testbed_dir: str = ".."):
        """name: name for service
           executor: node this service is running on
           service_type: the type of this service for easier identification
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)"""
        super().__init__(name, executor, service_type, image, cpu, cpu_allowance, memory)
        self.key_dir = key_dir
        self.testbed_dir = testbed_dir
        # Add testbed itself to upload
        self.add_file(os.path.abspath(pathlib.Path(testbed_dir + "/src")), pathlib.Path("/tmp/testbed"))
        # Add ssh keys to upload
        self.add_file(os.path.abspath(pathlib.Path(key_dir)), pathlib.Path("/tmp"))
        # Add testbed topology to service
        self.add_file(pathlib.Path(testbed_dir + "/testbed/work/current_topology.json"), pathlib.Path("/tmp"))

    @abstractmethod
    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        # Add ssh configuration
        config.add_command(Command(
            self.command_prefix() + "mkdir -p /etc/ssh && touch /etc/ssh/ssh_config && chmod 600 /etc/ssh/ssh_config"),
                           Command())
        for p in os.listdir(os.path.abspath(pathlib.Path(self.key_dir))):
            config.add_command(Command(self.command_prefix() + "bash -c " + LocalCommand.encapsule_command(
                f"echo \"IdentityFile /tmp/ssh_keys/{pathlib.Path(p).name}\" >> /etc/ssh/ssh_config")),
                               Command())

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(TestbedService, self).to_dict(without_gui), **{
            'key_dir': self.key_dir,
            'testbed_dir': self.testbed_dir
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'TestbedService':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.key_dir = in_dict['key_dir']
        ret.testbed_dir = in_dict['testbed_dir']
        return ret
