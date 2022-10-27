from abc import abstractmethod, ABC
from enum import Enum

from gui.gui_data_attachment import GuiDataAttachment
from topo.interface import Interface


class NodeType(Enum):
    LINUX_DEBIAN, LINUX_ARCH = range(2)


class Node(ABC):
    """A node that is used to execute services."""

    def __init__(self, name: str, node_type: NodeType, ssh_remote: str, ssh_port: int = 22,
                 ssh_work_dir: str = None):
        """name: the name of the node
           node_type: type of node for easier identification
           ssh_remote: the connection address for remote devices to connect to (e.g. root@10.0.1.1)
           ssh_port: the port used by remote devices to connect via ssh
           ssh_work_dir: the work dir used by external devices on this node (if None, no workdir switch)"""
        self.name = name
        self.type = node_type
        self.ssh_work_dir = ssh_work_dir
        self.intfs: list[Interface] = [Interface(name="lo").add_ip("127.0.0.1", "127.0.0.0/8")]
        self.current_virtual_device_num = 0
        self.ssh_remote = ssh_remote
        self.ssh_port = ssh_port
        self.gui_data: GuiDataAttachment = GuiDataAttachment()

    def get_ssh_base_command(self) -> str:
        if not self.ssh_remote:
            # Determine from interface
            for intf in self.intfs:
                for ip in intf.ips:
                    if not ip.is_loopback:
                        self.ssh_remote = f"root@{str(ip)}"
                        break
                if self.ssh_remote:
                    break
            if not self.ssh_remote:
                raise Exception("Can not ssh to node without external interfaces")
        return f"ssh -p {self.ssh_port} {self.ssh_remote}"

    def add_interface(self, intf: Interface) -> 'Node':
        for i in self.intfs:
            if i.name == intf:
                raise Exception(f"Interface with name {intf.name} already exists in node {self.name}")
        self.intfs.append(intf)
        return self

    def get_interface(self, intf: str) -> Interface:
        for i in self.intfs:
            if i.name == intf:
                return i
        return None

    def remove_interface(self, intf: str) -> Interface:
        found = None
        for i in self.intfs:
            if i.name == intf:
                found = i
                break
        if found:
            self.intfs.remove(found)
        return found

    def get_new_virtual_device_num(self) -> int:
        ret = self.current_virtual_device_num
        self.current_virtual_device_num += 1
        return ret

    @abstractmethod
    def get_configuration_builder(self, topo: 'Topo'):
        pass

    def to_dict(self) -> dict:
        intfs = []
        for i in self.intfs:
            intfs.append(i.to_dict())
        return {
            'class': type(self).__name__,
            'module': type(self).__module__,
            'name': self.name,
            'type': self.type.name,
            'ssh_remote': self.ssh_remote,
            'ssh_port': str(self.ssh_port),
            'ssh_work_dir': self.ssh_work_dir,
            'current_virtual_device_num': str(self.current_virtual_device_num),
            'intfs': intfs,
            'gui_data': self.gui_data.to_dict()
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Node':
        """Internal method to initialize from dictionary."""
        ret = cls(in_dict['name'],
                  NodeType[in_dict['type']], in_dict['ssh_remote'], int(in_dict['ssh_port']), in_dict['ssh_work_dir'])
        ret.current_virtual_device_num = int(in_dict['current_virtual_device_num'])
        ret.intfs.clear()
        for intf in in_dict['intfs']:
            ret.intfs.append(Interface.from_dict(intf))
        ret.gui_data = GuiDataAttachment.from_dict(in_dict['gui_data'])
        return ret
