import ipaddress
import os
import time

from config.configuration import Configuration
from config.export.ssh_exporter import SSHConfigurationExporter
from live.engine_component import EngineNode, EngineComponentStatus, EngineService, EngineInterfaceState, \
    EngineInterface
from live.engine_topology_change_listener import EngineTopologyChangeListener
from platforms.linux_server.lxc_service import LXCService
from ssh.ifstat_command import IfstatSSHCommand
from ssh.ip_addr_ssh_command import IpAddrSSHCommand, InterfaceState
from ssh.iperf_command import IperfSSHCommand, IperfClientSSHCommand
from ssh.lock_read_command import LockReadSSHCommand
from ssh.lock_write_command import LockWriteSSHCommand
from ssh.lxc_container_command import LxcContainerListCommand, LXCContainerStatus
from ssh.ping_ssh_command import PingSSHCommand
from ssh.ssh_command import SSHCommand
from ssh.tc_qdisc_command import TcQdiscSSHCommand
from topo.interface import Interface
from topo.node import Node
from topo.service import Service
from topo.topo import Topo, TopoUtil


class Engine(object):
    def __init__(self, topo: Topo or str or None,
                 local_node: Node or None = None):
        if not topo:
            cmd = LockReadSSHCommand(local_node, "/tmp", "current_topology.json")
            cmd.run()
            if cmd.content == "":
                raise Exception("No topo stored on current node and no topology given!")
            else:
                topo = Topo.import_topo(cmd.content)
        if isinstance(topo, str):
            topo = TopoUtil.from_file(topo)
        self.topo = topo
        self.altered_topo: Topo or None = None
        if not local_node:
            if len(topo.nodes) != 1:
                raise Exception("No nodes in topology or no local node given but using multi-node setup!")
            local_node = list(topo.nodes.values())[0]
        self.local_node = local_node
        self.nodes: dict[str, EngineNode] = {}
        for node in topo.nodes.values():
            self.nodes[node.name] = EngineNode(self, node, topo)
        self.stop_updating = False
        self.engine_topology_change_listeners: [EngineTopologyChangeListener] = []

    def continuous_update(self):
        while not self.stop_updating:
            self.synchronize_topologies()
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
            if self.nodes[component.executor.name].status != EngineComponentStatus.RUNNING:
                self.start(component.executor)
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
                for service in node.services:
                    self.stop(service)
                node.status = EngineComponentStatus.STOPPED
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

    def regress(self, old_topo: 'Topo', old_component: Node or Service, new_topo: 'Topo',
                new_component: Node or Service):
        if isinstance(old_component, Node):
            node = self.nodes[old_component.name]
            if node.status == EngineComponentStatus.RUNNING or node.status == EngineComponentStatus.STOPPED:
                old_config = old_component.get_configuration_builder(old_topo).build()
                exporter = SSHConfigurationExporter(old_config, old_component)
                exporter.regress_node(old_topo, old_config, new_component.get_configuration_builder(new_topo))
            elif node.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not regress node {old_component.name} because it is currently unreachable")
        elif isinstance(old_component, Service):
            service = self.nodes[old_component.executor.name].services[old_component.name]
            if service.status == EngineComponentStatus.RUNNING or service.status == EngineComponentStatus.STOPPED:
                old_config = old_component.get_configuration_builder(old_topo).build()
                exporter = SSHConfigurationExporter(old_config, old_component)
                exporter.regress(old_topo, new_component.get_configuration_builder(new_topo), old_component,
                                 new_component)
            elif service.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not regress service {old_component.name} because it is currently unreachable")

    def advance(self, old_topo: 'Topo', old_component: Node or Service, new_topo: 'Topo',
                new_component: Node or Service):
        if isinstance(new_component, Node):
            node = self.nodes[new_component.name]
            node.component = new_component
            if node.status == EngineComponentStatus.RUNNING or node.status == EngineComponentStatus.STOPPED:
                new_config = new_component.get_configuration_builder(new_topo).build()
                exporter = SSHConfigurationExporter(new_config, new_component)
                exporter.advance_node(new_topo, old_component.get_configuration_builder(old_topo).build(), new_config)
            elif node.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not advance node {new_component.name} because it is currently unreachable")
        elif isinstance(new_component, Service):
            service = self.nodes[new_component.executor.name].services[new_component.name]
            service.component = new_component
            if service.status == EngineComponentStatus.RUNNING or service.status == EngineComponentStatus.STOPPED:
                new_config = new_component.get_configuration_builder(new_topo).build()
                exporter = SSHConfigurationExporter(new_config, new_component)
                exporter.advance(new_topo, new_component.get_configuration_builder(new_topo), old_component,
                                 new_component)
            elif service.status == EngineComponentStatus.UNREACHABLE:
                raise Exception(f"Can not advance service {new_component.name} because it is currently unreachable")

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
                service.status = node.status
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
            tcqdisc = self.cmd_tc_qdisc(component.component)
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
                        if name in tcqdisc.results.keys():
                            intf.tcqdisc = tcqdisc.results[name]
                        else:
                            intf.tcqdisc = (0, 0, 0, 0, 0)
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
                intf.tcqdisc = (0, 0, 0, 0, 0)
                intf.ifstat = None
        pass

    def check_node_reachable(self, node: Node) -> EngineComponentStatus:
        command = self.cmd_ping(self.local_node, node, 1)
        if command.packets_received == 0:
            return EngineComponentStatus.UNREACHABLE
        else:
            command = self.cmd_ip_addr(node)
            bind_names = []
            self.topo.network_implementation.generate(node, Configuration())
            for link in self.topo.links:
                if link.service1 and link.service1.executor == node and link.intf1.bind_name:
                    bind_names.append(link.intf1.bind_name)
                elif link.service2 and link.service2.executor == node and link.intf2.bind_name:
                    bind_names.append(link.intf2.bind_name)
            for bind_name in bind_names:
                if bind_name not in [x[0] for x in command.results.values()]:
                    return EngineComponentStatus.REMOVED
            return EngineComponentStatus.RUNNING

    def cmd_ifstat(self, source: Service or Node, timeout: int = 5, consumer=None) -> IfstatSSHCommand:
        command = IfstatSSHCommand(source, timeout, consumer)
        command.run()
        return command

    def cmd_tc_qdisc(self, source: Service or Node) -> TcQdiscSSHCommand:
        command = TcQdiscSSHCommand(source)
        command.run()
        return command

    def cmd_iperf(self, source: Service, target: Service, target_device: Service or Interface, port: int = 1337,
                  interval_seconds: int = 1,
                  time_seconds: int = 10, server_options: str = "", client_options: str = "",
                  consumer=None) -> IperfClientSSHCommand:
        target_ip = self.calculate_ip(source, target_device)
        if not target_ip:
            raise Exception("Target not reachable")
        command = IperfSSHCommand(source, target, str(target_ip), port, interval_seconds, time_seconds,
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

    def cmd_ping(self, source: Service or Node, target: Service or Node or Interface, count: int or None = 4,
                 consumer=None) -> PingSSHCommand:
        if isinstance(source, Service) and (isinstance(target, Service) or isinstance(target, Interface)):
            target_ip = self.calculate_ip(source, target)
            if not target_ip:
                raise Exception("Target not reachable")
            command = PingSSHCommand(source, str(target_ip), count, consumer)
        elif isinstance(source, Node) and isinstance(target, Node):
            remote = target.ssh_remote
            while remote.__contains__("@"):
                remote = remote.split("@")[1]
            command = PingSSHCommand(source, remote, count, consumer)
        else:
            raise Exception("Can only ping cross service or cross node, not between service and node")
        command.run()
        return command

    def cmd_set_iface_state(self, target: EngineInterface, state: EngineInterfaceState):
        cmd = f"ip link set dev {target.component.name} {state.name.lower()}"
        if isinstance(target.parent, EngineService):
            SSHCommand(target.parent.parent.component,
                       target.parent.component.command_prefix() + cmd) \
                .run()
        else:
            SSHCommand(target.parent.component, cmd).run()
        if state == EngineInterfaceState.DOWN:
            target.status = EngineComponentStatus.STOPPED
        else:
            target.status = EngineComponentStatus.RUNNING
        target.interface_state = state

    def cmd_set_iface_qdisc(self, target: EngineInterface, delay: int, loss: float,
                            delay_variation: int = 0, delay_correlation: float = 0, loss_correlation: float = 0):
        cmd1 = f"tc qdisc delete dev {target.component.name} root netem &> /dev/null || true"
        cmd2 = f"tc qdisc add dev {target.component.name} root netem"
        if delay > 0:
            cmd2 += f" delay {delay}"
            if delay_variation > 0:
                cmd2 += f" {delay_variation}"
                if delay_correlation > 0:
                    cmd2 += f" {delay_correlation * 100}%"
        if loss > 0:
            cmd2 += f" loss {loss * 100}%"
            if loss_correlation > 0:
                cmd2 += f" {loss_correlation * 100}%"
        if isinstance(target.parent, EngineService):
            SSHCommand(target.parent.parent.component,
                       target.parent.component.command_prefix() + cmd1) \
                .run()
            SSHCommand(target.parent.parent.component,
                       target.parent.component.command_prefix() + cmd2) \
                .run()
        else:
            SSHCommand(target.parent.component, cmd1).run()
            SSHCommand(target.parent.component, cmd2).run()

    def calculate_ip(self, source: Service, target: Service or Interface) -> ipaddress:
        if isinstance(target, Service):
            if source == target:
                return ipaddress.ip_address("127.0.0.1")
            else:
                reachable_ips = source.build_routing_table(True)
                for ip in reachable_ips.keys():
                    if target.has_ip(ip):
                        return ip
            return None
        elif isinstance(target, Interface):
            if target in source.intfs:
                return ipaddress.ip_address("127.0.0.1")
            else:
                reachable_ips = source.build_routing_table(True)
                for ip in reachable_ips.keys():
                    if ip in target.ips:
                        return ip
            return None
        else:
            raise Exception("Target is neither Service nor Interface")

    def write_topology_to_all(self, topo: Topo):
        # Write with lock
        content = topo.export_topo()
        path = "/tmp/flush_topo.json"
        f = open(path, "w")
        f.write(content)
        f.close()
        for node in topo.nodes.values():
            cmd = LockWriteSSHCommand(node, "/tmp", "current_topology.json", path)
            cmd.run()
        os.remove(path)

    def get_local_node(self) -> EngineNode:
        return self.nodes.get(self.local_node.name)

    def synchronize_topologies(self):
        new_topo = self.get_local_node().read_topology()
        if new_topo:
            if not new_topo.eq_without_gui(self.topo):
                old_topo = self.topo
                self.topo = new_topo
                self.nodes.clear()
                for node in new_topo.nodes.values():
                    self.nodes[node.name] = EngineNode(self, node, new_topo)
                self.on_topology_change(old_topo, new_topo)
        else:
            self.write_topology_to_all(self.topo)

    def on_topology_change(self, old_topo: Topo, new_topo: Topo):
        for x in self.engine_topology_change_listeners:
            x.on_topology_change(old_topo, new_topo)

    def on_component_change(self, old_component: Service or Node or None, new_component: Service or Node or None):
        for x in self.engine_topology_change_listeners:
            x.on_component_change(old_component, new_component)

    def begin_topology_changes(self):
        if self.altered_topo:
            raise Exception("Testbed is already being edited!")
        self.altered_topo = Topo.import_topo(self.topo.export_topo())

    def flush_topology_changes(self):
        if not self.altered_topo:
            raise Exception("Testbed has not been edited!")
        old_topo = self.topo
        self.write_topology_to_all(self.altered_topo)
        self.topo = self.altered_topo
        self.altered_topo = None
        # Now build and deploy differences
        # 1) Delete all removed services/nodes, or services that have been altered around core parameters (node, cpu, ...)
        # 2) Build back all changed services/nodes
        # 3) Build changed services/nodes back up
        # [4) Create new services/nodes] -> to be done by other code (they should start their new services/nodes)

        # 1a) Services
        destroyed_services: [str] = []
        for x in old_topo.services.keys():
            old_service = old_topo.services.get(x)
            if x not in self.topo.services.keys():
                # Service got removed
                self.destroy(old_service)
                del self.nodes[old_service.executor.name].services[old_service.name]
                self.on_component_change(old_service, None)
                continue
            new_service = self.topo.services.get(x)
            if old_service.executor.name is not new_service.executor.name or type(old_service) != type(new_service):
                destroyed_services.append(old_service.name)
                self.destroy(old_service)
                continue
            if isinstance(old_service, LXCService):
                if old_service.cpu != new_service.cpu \
                        or old_service.memory != new_service.memory \
                        or old_service.cpu_allowance != new_service.cpu_allowance \
                        or old_service.image != new_service.image:
                    destroyed_services.append(old_service.name)
                    self.destroy(old_service)
                    continue

        # 1b) Nodes
        for x in old_topo.nodes.keys():
            if x not in self.topo.nodes.keys():
                self.destroy(old_topo.nodes.get(x))

        # 2a) Build back services that are currently started or stopped
        for x in old_topo.services.keys():
            old_service = old_topo.services.get(x)
            if x in self.topo.services.keys():
                new_service = self.topo.services.get(x)
                self.regress(old_topo, old_service, self.topo, new_service)

        # 2b) Build back nodes that are currently reachable
        # +3a) Advance nodes that are currently reachable
        for x in old_topo.nodes.keys():
            old_node = old_topo.nodes.get(x)
            if x in self.topo.nodes.keys():
                new_node = self.topo.nodes.get(x)
                self.regress(old_topo, old_node, self.topo, new_node)
                self.advance(old_topo, old_node, self.topo, new_node)
                self.on_component_change(old_node, new_node)

        # 3b) Advance services that are currently started or stopped
        for x in old_topo.services.keys():
            old_service = old_topo.services.get(x)
            if x in self.topo.services.keys():
                new_service = self.topo.services.get(x)
                self.advance(old_topo, old_service, self.topo, new_service)
                self.on_component_change(old_service, new_service)

        # 4a) Integrate new nodes into the engine
        for x in self.topo.nodes:
            if x not in old_topo.nodes.keys():
                self.nodes[x] = EngineNode(self, self.topo.nodes.get(x), self.topo)
                self.on_component_change(None, self.nodes[x])

        # 4b) Integrate new services into the engine
        for x in self.topo.services:
            if x not in old_topo.services.keys():
                service = self.topo.services.get(x)
                node = self.nodes[service.executor]
                node.services[x] = EngineService(self, service, node)
                self.on_component_change(None, node.services[x])

        # Post work: Update everything locally
        self.on_topology_change(old_topo, self.topo)
        self.update_all_status()
