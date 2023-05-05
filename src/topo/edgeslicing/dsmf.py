from platforms.linux_server.lxc_service import LXCService
from topo.service import ServiceType

class DomainSlice:
    def __init__(self, slice_id, config):
        self.config = config

        self.in_intf = config["id"]  # h1/2/3 -> s1
        self.out_intf = config["id"]  # s9 -> h4/5/6
        self.udp_port = 5000 + slice_id
        self.mpls_label_1 = 1000 + slice_id
        self.mpls_label_2 = 2000 + slice_id

        self.mpls_label_sfc_in_1 = 1100 + slice_id
        self.mpls_label_sfc_in_2 = 2100 + slice_id
        self.mpls_label_sfc_out_1 = 1200 + slice_id
        self.mpls_label_sfc_out_2 = 2200 + slice_id
        self.mpls_label_general = 9999

        self.src_name = config["src_name"]
        self.dst_name = config["dst_name"]
        self.sfc = config["sfc"]
        self.bw_max = config["bw_max"]
        self.bw_min = config["bw_min"]

        self.qos = {}

class DSMF(LXCService):
    """A controller is a service providing instructions to an OpenFlow switch."""

    def __init__(self, name: str, executor: 'Node', cpu: str = None,
                 cpu_allowance: str = None, memory: str = None,
                 port: int = 10000, bind_ip: str = '0.0.0.0'):
        """name: name for service
           executor: node this service is running on
           service_type: the type of this service for easier identification
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)
           port: the port to bind to (for switches to connect)
           protocol: typically tcp or udp"""
        super().__init__(name, executor, ServiceType.DSMF, "ryu", cpu, cpu_allowance, memory)
        self.port = port
        self.bind_ip = bind_ip
        self.qos = None
        self.switches = None
        self.core_controller_name = None
        self.core_controller_ip = None
        self.net_id = None
        self.net = None
        self.app = None
        self.max_rate = 100000000
        self.general_slice_bw = self.max_rate
        self.slices = {}

    def is_switch(self) -> bool:
        return False

    def is_controller(self) -> bool:
        return False

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(DSMF, self).to_dict(), **{
            'port': str(self.port),
            'bind_ip': self.bind_ip
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'DSMF':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.port = int(in_dict['port'])
        ret.bind_ip = in_dict['bind_ip']
        return ret