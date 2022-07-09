import re
from abc import ABC

from config.configuration import Command
from topo.interface import Interface
from topo.service import Service


class Switch(Service, ABC):
    """A Switch is a Node that is running an OpenFlow switch."""

    port_base = 1  # Switches start with port 1 in OpenFlow #TODO Remove?
    dpid_len = 16  # digits in dpid passed to switch

    def __init__(self, name, service_type: 'ServiceType', executor: 'Node', dpid=None, opts='', listen_port=None,
                 controllers: list['Controller'] = []):
        """dpid: dpid hex string (or None to derive from name, e.g. s1 -> 1)
           opts: additional switch options
           listenPort: port to listen on for dpctl connections"""
        super().__init__(name, service_type, executor)
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

    def __init__(self, name, service_type: 'ServiceType', executor: 'Node', dpid=None, opts='', listen_port=None,
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
        super().__init__(name, service_type, executor, dpid=dpid, opts=opts, listen_port=listen_port,
                         controllers=controllers)
        self.fail_mode = fail_mode
        self.datapath = datapath
        self.inband = inband
        self.protocols = protocols
        self.reconnectms = reconnectms
        self.stp = stp
        self._uuids = []  # controller UUIDs #TODO ?

    def intf_opts(self, intf: Interface):
        """Return OVS interface options for intf"""
        link = intf.links[0]  # TODO is this correct to assume?
        intf1, intf2 = link.intf_name1, link.intf_name2
        intf = intf2 if link.service1 != self else intf1
        peer = intf1 if link.service1 != self else intf2
        # ofport_request is not supported on old OVS
        opts = ' ofport_request=%s' % self.executor.get_occupied_ports(self.executor.get_interface(intf))
        # Patch ports don't work well with old OVS
        opts += ' type=patch options:peer=%s' % peer
        return '' if not opts else ' -- set Interface %s' % intf + opts

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
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        int(self.dpid, 16)  # DPID must be a hex string
        # Command to add interfaces
        intfs = ''.join(' -- add-port %s %s' % (self, intf) +
                        self.intf_opts(intf)
                        for intf in self.intfs
                        if len(intf.links) > 0)
        # Command to create controller entries
        clist = [(self.name + c.name, '%s:%s:%d' %
                  (c.protocol, c.ip, c.port))
                 for c in self.controllers]
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
        config.add_commmand(Command('ovs-vsctl ' + cargs +
                                    ' -- add-br %s' % self.name +
                                    ' -- set bridge %s controller=[%s]' % (self, cids) +
                                    self.bridge_opts() +
                                    intfs),
                            Command('ovs-vsctl del-br %s' % self.name))
        return
