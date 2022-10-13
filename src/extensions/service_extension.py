from abc import ABC, abstractmethod


class ServiceExtension(ABC):
    def __init__(self, name: str, service: 'Service'):
        self.name = name
        self.service = service
        self.claimed_interfaces: list[str] = []

    def to_dict(self) -> dict:
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'name': self.name
        }

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict, service: 'Service') -> 'ServiceExtension':
        """Internal method to initialize from dictionary."""
        ret = cls(in_dict['name'], service)
        return ret

    @abstractmethod
    def append_to_configuration(self, prefix: str, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        """Method to be implemented by every service extension definition"""
        pass

    @abstractmethod
    def append_to_configuration_pre_start(self, prefix: str, config_builder: 'ConfigurationBuilder',
                                          config: 'Configuration'):
        """Method to be implemented by every service extension definition"""
        pass
