from config.configuration import Command
from live.testbed_service import TestbedService
from ssh.localcommand import LocalCommand
from topo.node import Node
from topo.service import ServiceType


class DSMFService(TestbedService):
    """A service used to establish a DSMF for our edge-slicing project."""

    def __init__(self, name: str, executor: Node, image: str = "ryu", cpu: str = None,
                 cpu_allowance: str = None, memory: str = None, key_dir: str = "../ssh_keys", testbed_dir: str = ".."):
        """name: name for service
           executor: node this service is running on
           service_type: the type of this service for easier identification
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)"""
        super().__init__(name, executor, ServiceType.DSMF, image, cpu, cpu_allowance, memory, key_dir, testbed_dir)

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        config.add_command(Command(
            self.command_prefix() + "bash -c " + LocalCommand.encapsule_command("cd /tmp/testbed/src && python3 "
                                                                                "topo/edgeslicing/dsmf.py > "
                                                                                "/tmp/dsmf.log")),
                           Command())

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(DSMFService, self).to_dict(without_gui), **{
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'DSMFService':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        return ret

    def is_switch(self) -> bool:
        return False

    def is_controller(self) -> bool:
        return False
