from config.configuration import Command
from extensions.service_extension import ServiceExtension


class MacVlanServiceExtension(ServiceExtension):
    def __init__(self, name: str, service: 'Service', ssh_public_key: None or str = None):
        super().__init__(name, service)
        self.ssh_public_key: str = ssh_public_key
        self.claimed_interfaces.append("eth0")

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(MacVlanServiceExtension, self).to_dict(), **{
            'pub': self.ssh_public_key
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict, service: 'Service') -> 'MacVlanServiceExtension':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict, service)
        ret.ssh_public_key = in_dict['pub']
        return ret

    def append_to_configuration(self, prefix: str, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        if self.ssh_public_key:
            filename = f"/root/.ssh/authorized_keys"
            config.add_command(Command(f"{prefix} bash -c \"echo \\\"{self.ssh_public_key}\\\" "
                                       f"> {filename}\""),
                               Command())
            config.add_command(Command(f"{prefix} cd /root && /usr/sbin/sshd -D -f /etc/ssh/sshd_config &"),
                               Command())

    def append_to_configuration_pre_start(self, prefix: str, config_builder: 'ConfigurationBuilder',
                                          config: 'Configuration'):
        config.add_command(
            Command(f"lxc config device add {self.service.name} {self.name} nic nictype=macvlan parent={self.name}"),
            Command(f"lxc config device remove {self.service.name} {self.name}"))
        pass
