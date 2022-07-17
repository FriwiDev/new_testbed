import re
from abc import ABC

from config.configuration import Command
from platform.linux_server.lxc_service import LXCService
from topo.service import ServiceType


class Switch(LXCService, ABC):
    """A Switch is a Node that is running an OpenFlow switch."""

    port_base = 1  # Switches start with port 1 in OpenFlow #TODO Remove?
    dpid_len = 16  # digits in dpid passed to switch

    def __init__(self, name, executor: 'Node', service_type: 'ServiceType', image: str = "ubuntu", cpu: str = None,
                 memory: str = None, dpid=None, opts='', listen_port=None,
                 controllers: list['Controller'] = []):
        """dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections"""
        super().__init__(name, executor, service_type, image, cpu, memory)
        self.dpid = self.default_dpid(dpid)
        self.opts = opts
        self.listen_port = listen_port
        self.controllers = controllers

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
    """Open vSwitch switch. Depends on ovs-vsctl."""

    def __init__(self, name, executor: 'Node', cpu: str = None, memory: str = None,
                 dpid=None, opts='', listen_port=None,
                 controllers: list['Controller'] = [],
                 fail_mode='secure', datapath='kernel', inband=False, protocols=None, reconnectms=1000,
                 stp=False):
        """name: name for switch
           failMode: controller loss behavior (secure|standalone)
           datapath: userspace or kernel mode (kernel|user)
           inband: use in-band control (False)
           protocols: use specific OpenFlow version(s) (e.g. OpenFlow13)
                      Unspecified (or old OVS version) uses OVS default
           reconnectms: max reconnect timeout in ms (0/None for default)
           stp: enable STP (False, requires failMode=standalone)"""
        super().__init__(name, executor, ServiceType.OVS, "ovs", cpu, memory, dpid=dpid, opts=opts,
                         listen_port=listen_port, controllers=controllers)
        self.fail_mode = fail_mode
        self.datapath = datapath
        self.inband = inband
        self.protocols = protocols
        self.reconnectms = reconnectms
        self.stp = stp
        self._uuids = []  # controller UUIDs #TODO ?

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
        return opts

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration'):
        from platform.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
        super().append_to_configuration(config_builder, config)
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
        config.add_command(Command(self.lxc_prefix() +
                                   'ip link set dev ' + self.name + ' up'),
                           Command(self.lxc_prefix() +
                                   'ip link set dev ' + self.name + ' down'))
        return

    def is_switch(self) -> bool:
        return True

    def is_controller(self) -> bool:
        return False
