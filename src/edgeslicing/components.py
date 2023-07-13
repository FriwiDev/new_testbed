import ipaddress
import json
from enum import Enum

from config.configuration import Command
from platforms.linux_server.linux_configuration_builder import LinuxConfigurationBuilder
from platforms.linux_server.lxc_service import SimpleLXCHost
from ssh.localcommand import LocalCommand
from topo.controller import RyuController
from topo.service import Service
from topo.switch import OVSSwitch
from topo.topo import Topo


class Network(object):
    def __init__(self, name: str, reachable: [str], preferred_vpn: [str], subnets: [ipaddress.ip_network]):
        self.name = name
        self.reachable = reachable
        self.preferred_vpn = preferred_vpn
        self.subnets = subnets


class Connection(object):
    def __init__(self, intf_name: str, intf_id: int, other_end: str):
        self.intf_name = intf_name
        self.intf_id = intf_id
        self.other_end = other_end


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
    def __init__(self, network_name: str, device_name: str, device_type: DeviceType, connection: [Connection]):
        self.network_name = network_name
        self.device_name = device_name
        self.device_type = device_type,
        self.connection = connection


class Range(object):
    def __init__(self, fr: int, to: int):
        self.fr = fr
        self.to = to

class ESMFType(Enum):
    ESMF = 0
    CTMF = 1

class ESMFConfiguration(object):
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

    def __str__(self):
        return json.dumps(self)


class DSMFType(Enum):
    DSMF = 0
    DTMF = 1

class DSMFConfiguration(object):
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

    def __str__(self):
        return json.dumps(self)


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


class ESMF(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', network: str, coordinators: ['ESMF' or str],
                 vpn_gateways: ['VPNGateway'], networks: [Network], domain_controller: 'DSMF',
                 slice_id_range: Range, tunnel_id_range: Range,
                 reservable_bitrate: int = 1000000000, type: ESMFType = ESMFType.ESMF):
        super().__init__(name, executor, image="slicing-esmf")
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
                                           str(self.get_config(config_builder.topo))
                                       ) + " > config.json"
                                   ))
                           )
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "python3 -m esmf_server"),
                           Command())

    def get_config(self, topo: Topo) -> ESMFConfiguration:
        self.coordinators = [(topo.get_service(x) if isinstance(x, str) else x) for x in self.coordinators]
        co = [
            DeviceConfiguration(ip=x.get_valid_ip_for(self), port=8080, connections=Utils.get_connections(x),
                                network=x.network, name=x.name)
            for x in self.coordinators]
        vpns = [
            DeviceConfiguration(ip=x.get_valid_ip_for(self), port=8083, connections=Utils.get_connections(x),
                                network=x.network, name=x.name)
            for x in self.vpn_gateways]
        dc = DeviceConfiguration(ip=self.domain_controller.get_valid_ip_for(self), port=8081,
                                 connections=Utils.get_connections(self.domain_controller),
                                 network=self.domain_controller.network, name=self.domain_controller.name)
        return ESMFConfiguration(self.type, self.network, vpns, self.networks, co, dc, self.slice_id_range,
                                 self.tunnel_id_range, self.reservable_bitrate)

    def to_dict(self, without_gui: bool = False) -> dict:
        # Merge own data into super class data
        return {**super(SimpleLXCHost, self).to_dict(without_gui), **{
            'srv_type': self.type,
            'network': self.network,
            'coordinators': [x.name for x in self.coordinators],
            'vpns': [x.name for x in self.vpn_gateways],
            self.networks = networks  # TODO-NOW Serialization
            self.domain_controller = domain_controller
            self.slice_id_range = slice_id_range
            self.tunnel_id_range = tunnel_id_range
            self.reservable_bitrate = reservable_bitrate
        }}

    @classmethod
    def from_dict(cls, topo: 'Topo', in_dict: dict) -> 'ESMF':
        """Internal method to initialize from dictionary."""
        ret = super().from_dict(topo, in_dict)
        ret.image = in_dict['image']  # TODO-NOW Deserialization
        ret.cpu = in_dict['cpu']
        ret.memory = in_dict['memory']
        ret.files = [(Path(x['path']), Path(x['to'])) for x in in_dict['files']]
        return ret


class DSMF(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', network: str, controllers: ['EdgeslicingController'],
                 vpn_gateways: ['VPNGateway'],
                 networks: [Network], switches: [Service], network_borders: [NetworkBorderConfiguration],
                 reservable_bitrate: int = 1000000000, type: DSMFType = DSMFType.DSMF):
        super().__init__(name, executor, image="slicing-dsmf")
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
                                           str(self.get_config())
                                       ) + " > config.json"
                                   ))
                           )
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "python3 -m dsmf_server"),
                           Command())

    def get_config(self) -> DSMFConfiguration:
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
                                network=x.network, name=x.name)
            for x in self.switches]
        return DSMFConfiguration(self.type, self.network, co, vpns, sw, self.network_borders, self.networks,
                                 self.reservable_bitrate)


class EdgeslicingController(RyuController):
    def __init__(self, name: str, executor: 'Node', network: str):
        super().__init__(name, executor, script_path="../examples/defaults/simple_switch.py",  # TODO-NOW change to rest
                         image="slicing-controller")
        self.network = network


class VPNGateway(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', network: str):
        super().__init__(name, executor, image="slicing-vpn-gateway")
        self.network = network

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
        # Enable ip forwarding
        config.add_command(Command(self.lxc_prefix() + "sysctl -w net.ipv4.ip_forward=1"),
                           Command())
        # Run the module
        config.add_command(Command(self.lxc_prefix() + "python3 -m vpn_gateway_server"),
                           Command())


class QueueableOVSSwitch(OVSSwitch):
    def __init__(self, name, executor: 'Node', network: str, cpu: str = None, cpu_allowance: str = None,
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
        super().__init__(name, executor, "slicing-switch", cpu, cpu_allowance, memory,
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
        config.add_command(Command(self.lxc_prefix() + "python3 -m switch_server"),
                           Command())


class EdgeslicingLXCHost(SimpleLXCHost):
    def __init__(self, name: str, executor: 'Node', network: str):
        super().__init__(name, executor, image="slicing-host")
        self.network = network

    def append_to_configuration(self, config_builder: 'ConfigurationBuilder', config: 'Configuration', create: bool):
        super().append_to_configuration(config_builder, config, create)
        if not isinstance(config_builder, LinuxConfigurationBuilder):
            raise Exception("Can only configure OVS on Linux nodes")
