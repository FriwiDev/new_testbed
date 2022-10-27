import ipaddress
import re
from abc import ABC

from config.configuration import Command
from network.network_utils import NetworkUtils
from platforms.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from platforms.linux_server.lxc_service import LXCService
from topo.interface import Interface
from topo.service import ServiceType


class Switch(LXCService, ABC):
    """A Switch is a service that is running an OpenFlow switch."""

    dpid_len = 16  # digits in dpid passed to switch

    def __init__(self, name, executor: 'Node', service_type: 'ServiceType', image: str = "ubuntu", cpu: str = None,
                 cpu_allowance: str = None, memory: str = None, dpid: str = None, opts: str = '',
                 listen_port: int = None, controllers: list['Controller'] = None):
        """name: name for switch
           executor: node this service is running on
           service_type: the type of this service for easier identification
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)
           dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections
           controllers: the controllers to attach to this switch"""
        super().__init__(name, executor, service_type, image, cpu, cpu_allowance, memory)
        if controllers is None:
            controllers = []
        self.dpid = self.default_dpid(dpid)
        self.opts = opts
        self.listen_port = listen_port
        self.controllers = controllers

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(Switch, self).to_dict(), **{
            'dpid': self.dpid,
            'opts': self.opts,
            'listen_port': str(self.listen_port),
            'controllers': [cont.name for cont in self.controllers]
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'Switch':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.dpid = in_dict['dpid']
        ret.opts = in_dict['opts']
        ret.listen_port = None if in_dict['listen_port'] == "None" else int(in_dict['listen_port'])
        ret.controllers = [topo.get_service(name) for name in in_dict['controllers']]
        return ret

    def default_dpid(self, dpid=None):
        "Return correctly formatted dpid from dpid or switch name (s1 -> 1)"
        if dpid:
            # Remove any colons and make sure it's a good hex number
            dpid = dpid.replace(':', '')
            assert len(dpid) <= self.dpid_len and int(dpid, 16) >= 0
        else:
            # Use hex of the first number in the switch name
            nums = re.findall(r'\d+', self.name)
            if nums:
                dpid = hex(int(nums[0]))[2:]
            else:
                raise Exception('Unable to derive default datapath ID - '
                                'please either specify a dpid or use a '
                                'canonical switch name such as s23.')
        return '0' * (self.dpid_len - len(dpid)) + dpid


class OVSSwitch(Switch):
    """Open vSwitch switch."""

    def __init__(self, name, executor: 'Node', cpu: str = None, cpu_allowance: str = None, memory: str = None,
                 dpid=None, opts='', listen_port=None,
                 controllers: list['Controller'] = None,
                 fail_mode='secure', datapath='kernel', inband=False, protocols=None, reconnectms=1000,
                 stp=False, local_ip: ipaddress.ip_address or str or None = None,
                 local_network: ipaddress.ip_address or str or None = None,
                 local_mac: str or None = None):
        """name: name for switch
           executor: node this service is running on
           cpu: string limiting cpu core limits (None for unlimited, "n" for n cores)
           cpu_allowance: string limiting cpu usage(None for unlimited, "n%" for n% usage)
           memory: string limiting memory usage (None for unlimited, "nMB" for n MB limit, other units work as well)
           dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections
           failMode: controller loss behavior (secure|standalone)
           datapath: userspace or kernel mode (kernel|user)
           inband: use in-band control (False)
           protocols: use specific OpenFlow version(s) (e.g. OpenFlow13)
                      Unspecified (or old OVS version) uses OVS default
           reconnectms: max reconnect timeout in ms (0/None for default)
           stp: enable STP (False, requires failMode=standalone)
           local_ip: local ip address for switch device
           local_network: network for local_ip
           local_mac: mac address for local switch device"""
        super().__init__(name, executor, ServiceType.OVS, "ovs", cpu, cpu_allowance, memory, dpid=dpid, opts=opts,
                         listen_port=listen_port, controllers=controllers)
        self.fail_mode = fail_mode
        self.datapath = datapath
        self.inband = inband
        self.protocols = protocols
        self.reconnectms = reconnectms
        self.stp = stp
        self.local_ip = local_ip
        self.local_network = local_network
        self.local_mac = local_mac

    def configure(self, topo: 'Topo'):
        if not self.local_mac:
            self.local_mac = topo.network_implementation \
                .get_network_address_generator().generate_mac(self, Interface(self.name))
        if self.local_ip:
            if isinstance(self.local_ip, str):
                self.local_ip = ipaddress.ip_address(self.local_ip)
        else:
            self.local_ip = topo.network_implementation \
                .get_network_address_generator().generate_ip(self, Interface(self.name, self.local_mac))
        if self.local_network:
            if isinstance(self.local_network, str):
                self.local_network = ipaddress.ip_network(self.local_network)
        else:
            self.local_network = topo.network_implementation \
                .get_network_address_generator().generate_network(self, Interface(self.name, self.local_mac))

    def bridge_opts(self):
        """Return OVS bridge options"""
        opts = (' other_config:datapath-id=%s' % self.dpid +
                ' fail_mode=%s' % self.fail_mode)
        if not self.inband:
            opts += ' other-config:disable-in-band=true'
        if self.datapath == 'user':
            opts += ' datapath_type=netdev'
        if self.protocols:
            opts += ' protocols=%s' % self.protocols
        if self.stp and self.fail_mode == 'standalone':
            opts += ' stp_enable=true'
        opts += ' other-config:dp-desc=%s' % self.name
        opts += ' other-config:hwaddr=%s' % self.local_mac
        return opts

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        # Stop the vswitch daemon, if already running
        config.add_command(Command(self.lxc_prefix() + "service openvswitch-switch stop"),
                           Command())
        config.add_command(Command(self.lxc_prefix() + "service ovs-vswitchd stop"),
                           Command())
        config.add_command(Command(self.lxc_prefix() + "service ovsdb-server stop"),
                           Command())
        # Create work dir
        config.add_command(Command(self.lxc_prefix() + "rm -rf /var/run/openvswitch"),
                           Command())
        config.add_command(Command(self.lxc_prefix() + "mkdir /var/run/openvswitch"),
                           Command())
        # Start ovsdb
        config.add_command(Command(self.lxc_prefix() + "ovsdb-server --remote=punix:/var/run/openvswitch/db.sock "
                                                       "--remote=db:Open_vSwitch,Open_vSwitch,manager_options "
                                                       "--private-key=db:Open_vSwitch,SSL,private_key "
                                                       "--certificate=db:Open_vSwitch,SSL,certificate "
                                                       "--bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert "
                                                       "--log-file=/var/log/openvswitch/ovsdb-server.log "
                                                       "--pidfile --verbose --detach"),
                           Command())
        # Init ovs ctl
        config.add_command(Command(self.lxc_prefix() + "ovs-vsctl init"),
                           Command())
        # Launch daemon
        config.add_command(Command(self.lxc_prefix() + "ovs-vswitchd --pidfile --detach"),
                           Command())
        # Configure bridge
        int(self.dpid, 16)  # DPID must be a hex string
        # Command to add interfaces
        intfs = ''
        for intf in self.intfs:
            if len(intf.links) > 0 and not intf.other_end_service.is_controller():
                intfs += ' -- add-port %s %s' % (self.name, intf.name)
        # Command to create controller entries
        clist = []
        for c in self.controllers:
            found_ip = None
            for link in config_builder.topo.links:
                if link.intf1 in self.intfs or link.intf2 in self.intfs:
                    # We are connected to this link
                    other = link.intf1 if link.intf2 in self.intfs else link.intf2
                    for ip in other.ips:
                        if not ip.is_loopback:
                            # We found a non-loopback address that is reachable by us
                            found_ip = ip
                            break
                if found_ip is not None:
                    break
            if found_ip is None:
                raise Exception(f"Could not locate controller IP for controller {c.name} from switch {self.name}"
                                f" - is it reachable?")
            clist.append((self.name + c.name, '%s:%s:%d' % (c.protocol, found_ip, c.port)))

        if self.listen_port:
            clist.append((self.name + '-listen',
                          'ptcp:%s' % self.listen_port))
        ccmd = '-- --id=@%s create Controller target=\\"%s\\"'
        if self.reconnectms:
            ccmd += ' max_backoff=%d' % self.reconnectms
        cargs = ' '.join(ccmd % (name, target)
                         for name, target in clist)
        # Controller ID list
        cids = ','.join('@%s' % name for name, _target in clist)
        # Try to delete any existing bridges with the same name
        cargs += ' -- --if-exists del-br %s' % self.name
        # One ovs-vsctl command to rule them all!
        netnsname = "netns-" + self.name
        config.add_command(Command(self.lxc_prefix() +
                                   'ovs-vsctl ' + cargs +
                                   ' -- add-br %s' % self.name +
                                   ' -- set bridge %s controller=[%s]' % (self.name, cids) +
                                   self.bridge_opts() +
                                   intfs),
                           Command(self.lxc_prefix() +
                                   'ovs-vsctl del-br %s' % self.name))
        # Set switch interface up
        NetworkUtils.set_up(config, self.name, self.lxc_prefix())
        # Set ovs-system interface up
        NetworkUtils.set_up(config, 'ovs-system', self.lxc_prefix())
        # Add ip to switch device
        NetworkUtils.add_ip(config, self.name, self.local_ip, self.local_network, self.lxc_prefix())
        # Remove routes from all other devices to use switch device for all packets
        for intf in self.intfs:
            for i in range(0, len(intf.networks)):
                net = intf.networks[i]
                if not net.is_loopback:
                    # For some reason route exists when it is added on stop - maybe auto generated
                    config.add_command(Command(f"{self.lxc_prefix()} ip route del {str(net)} dev {intf.name} || true"),
                                       Command())
        return

    def is_switch(self) -> bool:
        return True

    def is_controller(self) -> bool:
        return False

    def to_dict(self) -> dict:
        # Merge own data into super class data
        return {**super(OVSSwitch, self).to_dict(), **{
            'fail_mode': self.fail_mode,
            'datapath': self.datapath,
            'inband': str(self.inband),
            'protocols': self.protocols,
            'reconnectms': str(self.reconnectms),
            'stp': str(self.stp),
            'local_ip': str(self.local_ip),
            'local_network': str(self.local_network),
            'local_mac': str(self.local_mac)
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'OVSSwitch':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.fail_mode = in_dict['fail_mode']
        ret.datapath = in_dict['datapath']
        ret.inband = str(in_dict['inband']).lower() == 'true'
        ret.protocols = in_dict['protocols']
        ret.reconnectms = int(in_dict['reconnectms'])
        ret.stp = str(in_dict['stp']).lower() == 'true'
        ret.local_ip = ipaddress.ip_address(in_dict['local_ip'])
        ret.local_network = ipaddress.ip_network(in_dict['local_network'])
        ret.local_mac = in_dict['local_mac']
        return ret
