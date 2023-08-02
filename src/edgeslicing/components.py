import ipaddress
import json
import pprint
from abc import ABC
from enum import Enum

from config.configuration import Command
from platforms.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from platforms.linux_server.lxc_service import SimpleLXCHost
from ssh.localcommand import LocalCommand
from topo.controller import RyuController
from topo.interface import Interface
from topo.service import Service
from topo.switch import OVSSwitch
from topo.topo import Topo


class Network(object):
    def __init__(self, name: str, reachable: [str], preferred_vpn: [str], subnets: [ipaddress.ip_network]):
        self.name = name
        self.reachable = reachable
        self.preferred_vpn = preferred_vpn
        self.subnets = subnets
        self.subnet = None if len(self.subnets) == 0 else self.subnets[0]

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'reachable': self.reachable,
            'preferred_vpn': self.preferred_vpn,
            'subnets': [str(x) for x in self.subnets]
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Network':
        """Internal method to initialize from dictionary."""
        return Network(
            name=in_dict['name'],
            reachable=in_dict['reachable'],
            preferred_vpn=in_dict['preferred_vpn'],
            subnets=[ipaddress.ip_network(x) for x in in_dict['subnets']]
        )


class Connection(object):
    def __init__(self, intf_name: str, intf_id: int, other_end: str):
        self.intf_name = intf_name
        self.intf_id = intf_id
        self.other_end = other_end

    def to_dict(self) -> dict:
        return {
            'intf_name': self.intf_name,
            'intf_id': str(self.intf_id),
            'other_end': self.other_end
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Connection':
        """Internal method to initialize from dictionary."""
        return Connection(
            intf_name=in_dict['intf_name'],
            intf_id=int(in_dict['intf_id']),
            other_end=in_dict['other_end']
        )


class DeviceConfiguration(object):
    def __init__(self, ip: ipaddress.ip_address, port: int, connections: [Connection], network: str, name: str,
                 dpid: str = None):
        self.ip = ip
        self.port = port
        self.connections = connections
        self.network = network
        self.name = name
        self.dpid = dpid


class ControllerConfiguration(object):
    def __init__(self, ip: ipaddress.ip_address, port: int, name: str):
        self.ip = ip
        self.port = port
        self.name = name


class DeviceType(Enum):
    SWITCH = 0
    VPN = 1
    HOST = 2


class NetworkBorderConfiguration(object):
    def __init__(self, network_name: str, device_name: str, device_type: DeviceType, connection: Connection):
        self.network_name = network_name
        self.device_name = device_name
        self.device_type = device_type
        self.connection = connection

    def to_dict(self) -> dict:
        return {
            'network_name': str(self.network_name),
            'device_name': str(self.device_name),
            'device_type': self.device_type.name,
            'connection': self.connection.to_dict()
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'NetworkBorderConfiguration':
        """Internal method to initialize from dictionary."""
        return NetworkBorderConfiguration(
            network_name=in_dict['network_name'],
            device_name=in_dict['device_name'],
            device_type=DeviceType[in_dict['device_type']],
            connection=Connection.from_dict(in_dict['connection'])
        )


class Range(object):
    def __init__(self, fr: int, to: int):
        self.fr = fr
        self.to = to

    def to_dict(self) -> dict:
        return {
            'fr': str(self.fr),
            'to': str(self.to)
        }

    @classmethod
    def from_dict(cls, in_dict: dict) -> 'Range':
        """Internal method to initialize from dictionary."""
        return Range(
            fr=int(in_dict['fr']),
            to=int(in_dict['to'])
        )

class AbstractConfiguration(object):

    def _convert(self, obj) -> dict or list or str or int or None:
        if obj is None:
            return None
        if isinstance(obj, list):
            ret = []
            for x in obj:
                ret.append(self._convert(x))
            return ret
        if isinstance(obj, str) or isinstance(obj, int):
            return obj
        if isinstance(obj, Enum):
            return obj.name
        if isinstance(obj, ipaddress.IPv4Address) or isinstance(obj, ipaddress.IPv6Address) \
                           or isinstance(obj, ipaddress.IPv4Network) or isinstance(obj, ipaddress.IPv6Network):
            return str(obj)
        ret = {}
        for x, y in obj.items() if isinstance(obj, dict) else vars(obj).items():
            ret[x] = self._convert(y)
        return ret

    def to_dict(self) -> dict:
        return self._convert(self)



class ESMFType(Enum):
    ESMF = 0
    CTMF = 1

class ESMFConfiguration(AbstractConfiguration):
    def __init__(self, type: ESMFType, network: str, vpn_gateways: [DeviceConfiguration], networks: [Network],
                 coordinators: [DeviceConfiguration], domain_controller: DeviceConfiguration, slice_id_range: Range,
                 tunnel_id_range: Range, reservable_bitrate: int = 1000000000):
        self.type = type
        self.network = network
        self.vpn_gateways = vpn_gateways
        self.networks = networks
        self.coordinators = coordinators
        self.domain_controller = domain_controller
        self.slice_id_range = slice_id_range
        self.tunnel_id_range = tunnel_id_range
        self.reservable_bitrate = reservable_bitrate


class DSMFType(Enum):
    DSMF = 0
    DTMF = 1

class DSMFConfiguration(AbstractConfiguration):
    def __init__(self, type: DSMFType, network: str, controllers: [ControllerConfiguration],
                 vpn_gateways: [DeviceConfiguration], switches: [DeviceConfiguration],
                 network_borders: [NetworkBorderConfiguration], networks: [Network],
                 reservable_bitrate: int = 1000000000):
        self.type = type
        self.network = network
        self.controllers = controllers
        self.vpn_gateways = vpn_gateways
        self.switches = switches
        self.network_borders = network_borders
        self.networks = networks
        self.reservable_bitrate = reservable_bitrate


class Utils(object):
    @classmethod
    def get_connections(cls, srv: Service) -> [Connection]:
        ret = []
        i = 0
        for x in srv.intfs:
            if x.other_end_service:
                ret.append(Connection(x.name, i, x.other_end_service.name))
            i += 1
        return ret

    @classmethod
    def get_connection(cls, srv: Service, target_net: str) -> Connection:
        i = 0
        for x in srv.intfs:
            if x.other_end_service and x.other_end_service.network == target_net:
                return Connection(x.name, i, x.other_end_service.name)
            i += 1
        return None


class ESMF(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', late_init: bool = False, network: str = None, coordinators: ['ESMF' or str] = None,
                 vpn_gateways: ['VPNGateway' or str] = None, networks: [Network] = None,
                 domain_controller: 'DSMF' or str = None,
                 slice_id_range: Range = None, tunnel_id_range: Range = None,
                 reservable_bitrate: int = 1000000000, type: ESMFType = ESMFType.ESMF):
        super().__init__(name, executor, late_init, image="slicing-esmf")
        self.type = type
        self.network = network
        self.coordinators = coordinators
        self.vpn_gateways = vpn_gateways
        self.networks = networks
        self.domain_controller = domain_controller
        self.slice_id_range = slice_id_range
        self.tunnel_id_range = tunnel_id_range
        self.reservable_bitrate = reservable_bitrate

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        # Copy config file
        config.add_command(Command(self.lxc_prefix() + "bash -c " +
                                       LocalCommand.encapsule_command(
                                           "echo " + LocalCommand.encapsule_command(
                                               json.dumps(self.get_config(config_builder.topo).to_dict())
                                           ) + " > domain_config.json"
                                       )
                                   ),
                           Command()
                           )
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "bash -c \"echo \\\"python3 -m esmf_server\\\" | at now\""),
                           Command(self.lxc_prefix() + "pkill python3"))

    def get_config(self, topo: Topo) -> ESMFConfiguration:
        self.coordinators = [(topo.get_service(x) if isinstance(x, str) else x) for x in self.coordinators]
        self.vpn_gateways = [(topo.get_service(x) if isinstance(x, str) else x) for x in self.vpn_gateways]
        self.domain_controller = topo.get_service(self.domain_controller) \
            if isinstance(self.domain_controller, str) \
            else self.domain_controller
        co = [
            DeviceConfiguration(ip=x.get_valid_ip_for(self), port=8080, connections=Utils.get_connections(x),
                                network=x.network, name=x.name)
            for x in self.coordinators]
        vpns = [
            DeviceConfiguration(ip=x.main_ip, port=8083, connections=Utils.get_connections(x),
                                network=x.network, name=x.name)
            for x in self.vpn_gateways]
        dc = DeviceConfiguration(ip=self.domain_controller.get_valid_ip_for(self), port=8081,
                                 connections=Utils.get_connections(self.domain_controller),
                                 network=self.domain_controller.network, name=self.domain_controller.name)
        return ESMFConfiguration(self.type, self.network, vpns, self.networks, co, dc, self.slice_id_range,
                                 self.tunnel_id_range, self.reservable_bitrate)

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(ESMF, self).to_dict(without_gui), **{
            'srv_type': self.type.name,
            'network': self.network,
            'coordinators': [x if isinstance(x, str) else x.name for x in self.coordinators],
            'vpns': [x if isinstance(x, str) else x.name for x in self.vpn_gateways],
            'networks': [x.to_dict() for x in self.networks],
            'domain_controller': self.domain_controller
                                    if isinstance(self.domain_controller, str)
                                    else self.domain_controller.name,
            'slice_id_range': self.slice_id_range.to_dict(),
            'tunnel_id_range': self.tunnel_id_range.to_dict(),
            'reservable_bitrate': self.reservable_bitrate
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'ESMF':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.type = ESMFType[in_dict['srv_type']]
        ret.network = in_dict['network']
        ret.coordinators = in_dict['coordinators']
        ret.vpn_gateways = in_dict['vpns']
        ret.networks = [Network.from_dict(x) for x in in_dict['networks']]
        ret.domain_controller = in_dict['domain_controller']
        ret.slice_id_range = Range.from_dict(in_dict['slice_id_range'])
        ret.tunnel_id_range = Range.from_dict(in_dict['tunnel_id_range'])
        ret.reservable_bitrate = int(in_dict['reservable_bitrate'])
        return ret


class DSMF(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', late_init: bool = False, network: str = None,
                 controllers: ['EdgeslicingController'] = None, vpn_gateways: ['VPNGateway'] = None,
                 networks: [Network] = None, switches: [Service] = None,
                 network_borders: [NetworkBorderConfiguration] = None,
                 reservable_bitrate: int = 1000000000, type: DSMFType = DSMFType.DSMF):
        super().__init__(name, executor, late_init, image="slicing-dsmf")
        self.type = type
        self.network = network
        self.controllers = controllers
        self.vpn_gateways = vpn_gateways
        self.switches = switches
        self.network_borders = network_borders
        self.networks = networks
        self.reservable_bitrate = reservable_bitrate

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        # Copy config file
        config.add_command(Command(self.lxc_prefix() + "bash -c " +
                                       LocalCommand.encapsule_command(
                                           "echo " + LocalCommand.encapsule_command(
                                               json.dumps(self.get_config(config_builder.topo).to_dict())
                                           ) + " > domain_config.json"
                                       )
                                   ),
                           Command()
                           )
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "bash -c \"echo \\\"python3 -m dsmf_server\\\" | at now\""),
                           Command(self.lxc_prefix() + "pkill python3"))

    def get_config(self, topo: Topo) -> DSMFConfiguration:
        self.controllers = [(topo.get_service(x) if isinstance(x, str) else x) for x in self.controllers]
        self.vpn_gateways = [(topo.get_service(x) if isinstance(x, str) else x) for x in self.vpn_gateways]
        self.switches = [(topo.get_service(x) if isinstance(x, str) else x) for x in self.switches]
        co = [
            DeviceConfiguration(ip=x.get_valid_ip_for(self), port=8080, connections=Utils.get_connections(x),
                                network=x.network, name=x.name)
            for x in self.controllers]
        vpns = [
            DeviceConfiguration(ip=x.get_valid_ip_for(self), port=8083, connections=Utils.get_connections(x),
                                network=x.network, name=x.name)
            for x in self.vpn_gateways]
        sw = [
            DeviceConfiguration(ip=x.get_valid_ip_for(self), port=8082, connections=Utils.get_connections(x),
                                network=x.network, name=x.name, dpid=x.dpid)
            for x in self.switches]
        return DSMFConfiguration(self.type, self.network, co, vpns, sw, self.network_borders, self.networks,
                                 self.reservable_bitrate)

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(DSMF, self).to_dict(without_gui), **{
            'srv_type': self.type.name,
            'network': self.network,
            'controllers': [x if isinstance(x, str) else x.name for x in self.controllers],
            'vpns': [x if isinstance(x, str) else x.name for x in self.vpn_gateways],
            'switches': [x if isinstance(x, str) else x.name for x in self.switches],
            'networks': [x.to_dict() for x in self.networks],
            'network_borders': [x.to_dict() for x in self.network_borders],
            'reservable_bitrate': self.reservable_bitrate
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'DSMF':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.type = DSMFType[in_dict['srv_type']]
        ret.network = in_dict['network']
        ret.controllers = in_dict['controllers']
        ret.vpn_gateways = in_dict['vpns']
        ret.switches = in_dict['switches']
        ret.networks = [Network.from_dict(x) for x in in_dict['networks']]
        ret.network_borders = [NetworkBorderConfiguration.from_dict(x) for x in in_dict['network_borders']]
        ret.reservable_bitrate = int(in_dict['reservable_bitrate'])
        return ret


class EdgeslicingController(RyuController):
    def __init__(self, name: str, executor: 'Node', late_init: bool = False, network: str = None):
        super().__init__(name, executor, late_init, script_path="../examples/defaults/ofctl_rest.py",
                         image="slicing-controller")
        self.network = network

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(EdgeslicingController, self).to_dict(without_gui), **{
            'network': self.network
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'EdgeslicingController':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.network = in_dict['network']
        return ret


class VPNGateway(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', late_init: bool = False, network: str = None):
        super().__init__(name, executor, late_init, image="slicing-vpn-gateway")
        self.network = network

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        # Enable ip forwarding
        config.add_command(Command(self.lxc_prefix() + "sysctl -w net.ipv4.ip_forward=1"),
                           Command())
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "bash -c \"echo \\\"python3 -m vpn_gateway_server\\\" | at now\""),
                           Command(self.lxc_prefix() + "pkill python3"))

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(VPNGateway, self).to_dict(without_gui), **{
            'network': self.network
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'VPNGateway':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.network = in_dict['network']
        return ret


class QueueableOVSSwitch(OVSSwitch):
    def __init__(self, name, executor: 'Node', late_init: bool = False, network: str = None, cpu: str = None, cpu_allowance: str = None,
                 memory: str = None, dpid=None, opts='', listen_port=None,
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
        super().__init__(name, executor, late_init, "slicing-ovs", cpu, cpu_allowance, memory,
                         dpid, opts, listen_port,
                         controllers,
                         fail_mode, datapath, inband, protocols, reconnectms,
                         stp, local_ip,
                         local_network,
                         local_mac)
        self.network = network

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "bash -c \"echo \\\"python3 -m switch_server\\\" | at now\""),
                           Command(self.lxc_prefix() + "pkill python3"))

    def is_switch_exclude(self, intf: Interface):
        return isinstance(intf.other_end_service, DSMF)

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(QueueableOVSSwitch, self).to_dict(without_gui), **{
            'network': self.network
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'QueueableOVSSwitch':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.network = in_dict['network']
        return ret


class EdgeslicingLXCHost(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', late_init: bool = False, network: str = None):
        super().__init__(name, executor, late_init, image="slicing-host")
        self.network = network

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(EdgeslicingLXCHost, self).to_dict(without_gui), **{
            'network': self.network
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'EdgeslicingLXCHost':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.network = in_dict['network']
        return ret
