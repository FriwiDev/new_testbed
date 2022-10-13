import ipaddress
import time

from config.export.ssh_exporter import SSHConfigurationExporter
from live.engine_component import EngineNode, EngineComponentStatus, EngineService, EngineInterfaceState
from platforms.linux_server.linux_node import LinuxNode
from ssh.ifstat_command import IfstatSSHCommand
from ssh.ip_addr_ssh_command import IpAddrSSHCommand, InterfaceState
from ssh.iperf_command import IperfSSHCommand, IperfClientSSHCommand
from ssh.lxc_container_command import LxcContainerListCommand, LXCContainerStatus
from ssh.ping_ssh_command import PingSSHCommand
from topo.node import Node, NodeType
from topo.service import Service
from topo.topo import Topo, TopoUtil


class Engine(object):
    def __init__(self, topo: Topo or str, local_node: Node = LinuxNode("local", NodeType.LINUX_ARCH, "root@localhost")):
        if isinstance(topo, str):
            topo = TopoUtil.from_file(topo)
        self.topo = topo
        self.local_node = local_node
        self.nodes: dict[str, EngineNode] = {}
        for node in topo.nodes.values():
            self.nodes[node.name] = EngineNode(self, node, topo)
        self.stop_updating = False

    def continuous_update(self):
        while not self.stop_updating:
            self.update_all_status()
            time.sleep(10)

    def continuous_ifstat(self, subject: EngineService or EngineNode):
        while not self.stop_updating:
            start = time.time()
            if subject.status == EngineComponentStatus.RUNNING:
                self.cmd_ifstat(subject.component, 5, lambda itf, rx, tx: self._set_ifstat_data(subject, itf, rx, tx))
            stop = time.time()
            time.sleep((start - stop + 10) % 1)

    def get_status(self, subject: Service or Node) -> EngineComponentStatus:
        if isinstance(subject, Node):
            if subject.name in self.nodes.keys():
                return self.nodes[subject.name].status
            return EngineComponentStatus.UNREACHABLE
        elif isinstance(subject, Service):
            if subject.executor.name in self.nodes.keys():
                node = self.nodes[subject.executor.name]
                if subject.name in node.services.keys():
                    return node.services[subject.name].status
            return EngineComponentStatus.UNREACHABLE
        else:
            raise Exception("Subject is neither service nor node")

    def _set_ifstat_data(self, subject: Service or Node, itf: str, rx: int, tx: int):
        if itf in subject.intfs.keys():
            subject.intfs[itf].ifstat = (rx, tx)

    def start_all(self):
        for node in self.nodes.values():
            if node.status != EngineComponentStatus.UNREACHABLE:
                self.start(node.component)
                for service in node.services.values():
                    self.start(service.component)

    def stop_all(self):
        for node in self.nodes.values():
            if node.status != EngineComponentStatus.UNREACHABLE:
                for service in node.services.values():
                    self.stop(service.component)
                self.stop(node.component)

    def destroy_all(self):
        for node in self.nodes.values():
            if node.status != EngineComponentStatus.UNREACHABLE:
                for service in node.services.values():
                    self.destroy(service.component)
                self.destroy(node.component)

    def start(self, component: Node or Service):
        if isinstance(component, Node):
            node = self.nodes[component.name]
            if node.status != EngineComponentStatus.UNREACHABLE:
                is_already_created = False
                for service in node.services.values():
                    if service.status == EngineComponentStatus.RUNNING or service.status == EngineComponentStatus.STOPPED:
                        is_already_created = True
                        break
                if is_already_created:
                    return
                config = node.component.get_configuration_builder(self.topo).build()
                exporter = SSHConfigurationExporter(config, node.component)
                exporter.start_node(self.topo, node.component.get_configuration_builder(self.topo))
                node.status = EngineComponentStatus.RUNNING
            else:
                raise Exception(f"Can not start node {component.name} because it is currently unreachable")
        elif isinstance(component, Service):
            service = self.nodes[component.executor.name].services[component.name]
            if service.status == EngineComponentStatus.REMOVED:
                config = component.executor.get_configuration_builder(self.topo).build()
                exporter = SSHConfigurationExporter(config, component.executor)
                exporter.create(self.topo, component.executor.get_configuration_builder(self.topo), service.component)
                service.status = EngineComponentStatus.RUNNING
            elif service.status == EngineComponentStatus.STOPPED:
                config = component.executor.get_configuration_builder(self.topo).build()
                exporter = SSHConfigurationExporter(config, component.executor)
                exporter.start(self.topo, component.executor.get_configuration_builder(self.topo), service.component)
                service.status = EngineComponentStatus.RUNNING
            elif service.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not start service {component.name} because it is currently unreachable")

    def stop(self, component: Node or Service):
        if isinstance(component, Node):
            node = self.nodes[component.name]
            if node.status != EngineComponentStatus.UNREACHABLE:
                # TODO maybe disable interfaces?
                for service in node.services:
                    self.stop(service)
            else:
                raise Exception(f"Can not stop node {component.name} because it is currently unreachable")
        elif isinstance(component, Service):
            service = self.nodes[component.executor.name].services[component.name]
            if service.status == EngineComponentStatus.RUNNING:
                config = component.executor.get_configuration_builder(self.topo).build()
                exporter = SSHConfigurationExporter(config, component.executor)
                exporter.stop(self.topo, component.executor.get_configuration_builder(self.topo), service.component)
                service.status = EngineComponentStatus.STOPPED
            elif service.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not stop service {component.name} because it is currently unreachable")

    def destroy(self, component: Node or Service):
        if isinstance(component, Node):
            node = self.nodes[component.name]
            if node.status != EngineComponentStatus.UNREACHABLE:
                for service in node.services:
                    self.destroy(service)
                config = node.component.get_configuration_builder(self.topo).build()
                exporter = SSHConfigurationExporter(config, node.component)
                exporter.stop_node(self.topo, node.component.get_configuration_builder(self.topo))
                node.status = EngineComponentStatus.REMOVED
            else:
                raise Exception(f"Can not destroy node {component.name} because it is currently unreachable")
        elif isinstance(component, Service):
            service = self.nodes[component.executor.name].services[component.name]
            if service.status == EngineComponentStatus.RUNNING or service.status == EngineComponentStatus.STOPPED:
                config = component.executor.get_configuration_builder(self.topo).build()
                exporter = SSHConfigurationExporter(config, component.executor)
                exporter.remove(self.topo, component.executor.get_configuration_builder(self.topo), service.component)
                service.status = EngineComponentStatus.REMOVED
            elif service.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not destroy service {component.name} because it is currently unreachable")

    def update_all_status(self):
        for node in self.nodes.values():
            node.status = self.check_node_reachable(node.component)
            self.update_node_status(node)

    def update_node_status(self, node: EngineNode):
        if node.status == EngineComponentStatus.RUNNING:
            command = self.cmd_lxc_container_list(node.component)
            for service in node.services.values():
                if service.component.name in command.results.keys():
                    if command.results[service.component.name] == LXCContainerStatus.STOPPED:
                        service.status = EngineComponentStatus.STOPPED
                    elif command.results[service.component.name] == LXCContainerStatus.RUNNING:
                        service.status = EngineComponentStatus.RUNNING
                else:
                    service.status = EngineComponentStatus.REMOVED
                self.update_service_status(service)
        else:
            for service in node.services.values():
                service.status = EngineComponentStatus.UNREACHABLE
                self.update_service_status(service)
        self.update_interface_status(node)
        pass

    def update_service_status(self, service: EngineService):
        if service.status == EngineComponentStatus.UNREACHABLE:
            self.update_interface_status(service)
        else:
            self.update_interface_status(service)
        pass

    def update_interface_status(self, component: EngineNode or EngineService):
        if component.status == EngineComponentStatus.RUNNING:
            command = self.cmd_ip_addr(component.component)
            for intf in component.intfs.values():
                found = False
                for name, state, addr, ipaddr in command.results.values():
                    if name == intf.component.name:
                        found = True
                        if state == InterfaceState.UP or state == InterfaceState.UNKNOWN:
                            intf.status = EngineComponentStatus.RUNNING
                        else:
                            intf.status = EngineComponentStatus.STOPPED
                        intf.interface_state = EngineInterfaceState[state.name]
                        intf.live_mac = addr
                        intf.live_ips = ipaddr
                        break
                if not found:
                    intf.status = EngineComponentStatus.REMOVED
                    intf.interface_state = EngineInterfaceState.UNKNOWN
                    intf.live_mac = None
                    intf.live_ips = []
        else:
            for intf in component.intfs.values():
                intf.status = EngineComponentStatus.UNREACHABLE
                intf.interface_state = EngineInterfaceState.UNKNOWN
                intf.live_mac = None
                intf.live_ips = []
        pass

    def check_node_reachable(self, node: Node) -> EngineComponentStatus:
        command = self.cmd_ping(self.local_node, node, 1)
        if command.packets_received == 0:
            return EngineComponentStatus.UNREACHABLE
        else:
            return EngineComponentStatus.RUNNING

    def cmd_ifstat(self, source: Service or Node, timeout: int = 5, consumer=None) -> IfstatSSHCommand:
        command = IfstatSSHCommand(source, timeout, consumer)
        command.run()
        return command

    def cmd_iperf(self, source: Service, target: Service, port: int = 1337, interval_seconds: int = 1,
                  time_seconds: int = 10, server_options: str = "", client_options: str = "",
                  consumer=None) -> IperfClientSSHCommand:
        command = IperfSSHCommand(source, target, port, interval_seconds, time_seconds,
                                  server_options, client_options, consumer)
        command.run()
        return command.client

    def cmd_lxc_container_list(self, source: Node) -> LxcContainerListCommand:
        command = LxcContainerListCommand(source)
        command.run()
        return command

    def cmd_ip_addr(self, source: Service or Node) -> IpAddrSSHCommand:
        command = IpAddrSSHCommand(source)
        command.run()
        return command

    def cmd_ping(self, source: Service or Node, target: Service or Node, count: int or None = 4,
                 consumer=None) -> PingSSHCommand:
        if isinstance(source, Service) and isinstance(target, Service):
            command = PingSSHCommand(source, str(self.calculate_ip(source, target)), count, consumer)
        elif isinstance(source, Node) and isinstance(target, Node):
            remote = target.ssh_remote
            while remote.__contains__("@"):
                remote = remote.split("@")[1]
            command = PingSSHCommand(source, remote, count, consumer)
        else:
            raise Exception("Can only ping cross service or cross node, not between service and node")
        command.run()
        return command

    def calculate_ip(self, source: Service, target: Service) -> ipaddress:
        target_ip = None
        if source == target:
            target_ip = ipaddress.ip_address("127.0.0.1")
        else:
            reachable_ips = source.build_routing_table()
            for ip in reachable_ips.keys():
                if target.has_ip(ip):
                    target_ip = ip
        if not target_ip:
            raise Exception("Target not reachable")
        return target_ip
