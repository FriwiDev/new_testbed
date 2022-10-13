from extensions.macvlan_extension import MacVlanServiceExtension
from topo.interface import Interface


class MacVlanExtensionBuilder(object):
    def __init__(self, host_intf: Interface, service: 'Service', ssh_pub_key: str or None = None):
        self.host_intf = host_intf
        self.service = service
        self.ssh_pub_key = ssh_pub_key

    def build(self):
        ext = MacVlanServiceExtension(self.host_intf.name, self.service, self.ssh_pub_key)
        self.service.intfs.append(Interface("eth0"))
        self.service.add_extension(ext)
