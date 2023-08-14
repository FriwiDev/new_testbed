import sys
import time

from live.engine import Engine
from live.engine_component import EngineInterfaceState
from network.network_utils import NetworkUtils
from topo.interface import Interface
from topo.node import Node
from topo.service import Service


def main(argv: typing.List[str]):
    if len(argv) < 2:
        print("Script requires two or more arguments!")
        exit(1)

    engine = Engine(argv[0], None if len(argv) < 3 else argv[2])
    engine.update_all_status()

    if argv[1].lower() == "start_all":
        engine.start_all()
    elif argv[1].lower() == "stop_all":
        engine.stop_all()
    elif argv[1].lower() == "destroy_all":
        engine.destroy_all()
    elif argv[1].lower() == "start" or argv[1].lower() == "stop" or argv[1].lower() == "destroy":
        if len(argv) == 2:
            print("You need to supply some services or nodes!")
            exit(1)
        nodes = resolve_nodes(argv[2:], engine)
        services = resolve_services(argv[2:], engine)
        if argv[1].lower() == "start":
            for node in nodes:
                engine.start(node)
            for service in services:
                engine.start(service)
        elif argv[1].lower() == "stop":
            for service in services:
                engine.stop(service)
            for node in nodes:
                engine.stop(node)
        elif argv[1].lower() == "destroy":
            for service in services:
                engine.destroy(service)
            for node in nodes:
                engine.destroy(node)
    elif argv[1].lower() == "ping":
        if len(argv) != 4:
            print("./remote_topology.sh ping <service1> <service2[:intf]>")
            exit(1)
        if argv[2] in engine.topo.services.keys():
            spl = argv[3].split(":")
            if spl[0] in engine.topo.services.keys():
                target = engine.topo.services[spl[0]]
                if len(spl) > 1:
                    target_device = None
                    for dev in target.intfs:
                        if dev.name == spl[1]:
                            target_device = dev
                            break
                    if not target_device:
                        print("No such interface: " + argv[3])
                        exit(1)
                        return
                else:
                    target_device = target
                engine.cmd_ping(engine.topo.services[argv[2]], target_device, 4, handle_ping_result)
            else:
                print("No such service: " + argv[3])
                exit(1)
        else:
            print("No such service: " + argv[2])
            exit(1)
    elif argv[1].lower() == "iperf":
        if len(argv) < 4:
            print(
                "./remote_topology.sh iperf <service1> <service2[:intf]> [port] [interval] [time] "
                "[<client options> [| <server options>]]")
            exit(1)
        port = 1337
        if len(argv) > 4:
            port = int(argv[4])
        interval = 1
        if len(argv) > 5:
            interval = int(argv[5])
        time_dur = 10
        if len(argv) > 6:
            time_dur = int(argv[6])
        client_options = ""
        server_options = ""
        if len(argv) > 7:
            client = True
            for i in range(7, len(argv)):
                if argv[i] == "|":
                    client = False
                    continue
                if client:
                    client_options += argv[i] + " "
                else:
                    server_options += argv[i] + " "

        if argv[2] in engine.topo.services.keys():
            spl = argv[3].split(":")
            if spl[0] in engine.topo.services.keys():
                target = engine.topo.services[spl[0]]
                if len(spl) > 1:
                    target_device = None
                    for dev in target.intfs:
                        if dev.name == spl[1]:
                            target_device = dev
                            break
                    if not target_device:
                        print("No such interface: " + argv[3])
                        exit(1)
                        return
                else:
                    target_device = target
                engine.cmd_iperf(engine.topo.services[argv[2]], target, target_device, port, interval, time_dur,
                                 client_options, server_options, handle_iperf_result)
            else:
                print("No such service: " + argv[3])
                exit(1)
        else:
            print("No such service: " + argv[2])
            exit(1)
    elif argv[1].lower() == "ifstat":
        if len(argv) != 4:
            print("./remote_topology.sh ifstat <service|node> <intf>")
            exit(1)
        nodes = resolve_nodes(argv[2:3], engine)
        services = resolve_services(argv[2:3], engine)
        executor = nodes[0] if len(nodes) > 0 else services[0]
        i: Interface or None = None
        for intf in executor.intfs:
            if intf.name == argv[3]:
                i = intf
                break
        if not i:
            print(f"Unknown interface: {argv[3]}")
            exit(1)
        while True:
            start = time.time()
            engine.cmd_ifstat(executor, 5, lambda itf, rx, tx: print_intf(i.name, itf, rx, tx))
            stop = time.time()
            time.sleep((start - stop + 10) % 1)
    elif argv[1].lower() == "up":
        if len(argv) != 4:
            print("./remote_topology.sh up <service|node> <intf>")
            exit(1)
        nodes = resolve_nodes(argv[2:3], engine)
        services = resolve_services(argv[2:3], engine)
        executor = engine.nodes[nodes[0].name] if len(nodes) > 0 else \
            engine.nodes[services[0].executor.name].services[services[0].name]
        if argv[3] in executor.intfs.keys():
            engine.cmd_set_iface_state(executor.intfs[argv[3]], EngineInterfaceState.UP)
            return
        print(f"Unknown interface: {argv[3]}")
        exit(1)
    elif argv[1].lower() == "down":
        if len(argv) != 4:
            print("./remote_topology.sh down <service|node> <intf>")
            exit(1)
        nodes = resolve_nodes(argv[2:3], engine)
        services = resolve_services(argv[2:3], engine)
        executor = engine.nodes[nodes[0].name] if len(nodes) > 0 else \
            engine.nodes[services[0].executor.name].services[services[0].name]
        if argv[3] in executor.intfs.keys():
            engine.cmd_set_iface_state(executor.intfs[argv[3]], EngineInterfaceState.DOWN)
            return
        print(f"Unknown interface: {argv[3]}")
        exit(1)
    elif argv[1].lower() == "setqdisc":
        if len(argv) < 4:
            print(
                "./remote_topology.sh setqdisc <service|node> <intf> [<delay(ms)> [<delay-variation(ms)> [<delay-correlation(0;1)> [<loss(0;1)> [<loss-correlation(0;1)>]]]]]")
            exit(1)
        nodes = resolve_nodes(argv[2:3], engine)
        services = resolve_services(argv[2:3], engine)
        executor = engine.nodes[nodes[0].name] if len(nodes) > 0 else \
            engine.nodes[services[0].executor.name].services[services[0].name]
        if argv[3] in executor.intfs.keys():
            delay = int(argv[4]) if len(argv) > 4 else 0
            delay_variation = int(argv[5]) if len(argv) > 5 else 0
            delay_correlation = float(argv[6]) if len(argv) > 6 else 0
            loss = float(argv[7]) if len(argv) > 7 else 0
            loss_correlation = float(argv[8]) if len(argv) > 8 else 0
            engine.cmd_set_iface_qdisc(executor.intfs[argv[3]], delay, loss,
                                       delay_variation, delay_correlation, loss_correlation)
            return
        print(f"Unknown interface: {argv[3]}")
        exit(1)
    else:
        print("Unknown action " + argv[1])
        exit(1)


def handle_ping_result(seq, x):
    if isinstance(x, str):
        print(f"[{seq}] Error while pinging: {x}")
    else:
        ttl, duration = x
        print(f"[{seq}] Ping result: ttl={ttl} time={duration}")


def handle_iperf_result(from_sec: int, to_sec: int, transfer: float, bandwidth: float):
    print(f"[{from_sec}-{to_sec}] Transfer: {NetworkUtils.format_bytes(transfer)}Bytes  "
          f"Bandwidth: {NetworkUtils.format_bytes(bandwidth)}Bits")


def resolve_nodes(argv: typing.List[str], engine: Engine) -> typing.List[Node]:
    nodes: typing.List[Node] = []
    for s in argv:
        if s.startswith("service:"):
            continue
        if s.startswith("node:"):
            node_name = s.removeprefix("node:")
            if node_name in engine.topo.nodes.keys():
                nodes.append(engine.topo.nodes[node_name])
                continue
            else:
                print(f"Unknown node: {node_name}")
                exit(1)
        if s in engine.topo.nodes.keys():
            if s in engine.topo.services.keys():
                print(f"Ambiguous node or service: {s} - please prepend with node: or service: to signal intention")
                exit(1)
            nodes.append(engine.topo.nodes[s])
        elif s not in engine.topo.services.keys():
            print(f"Neither a valid node nor service: {s}")
            exit(1)
    return nodes


def resolve_services(argv: typing.List[str], engine: Engine) -> typing.List[Service]:
    services: typing.List[Service] = []
    for s in argv:
        if s.startswith("node:"):
            continue
        if s.startswith("service:"):
            service_name = s.removeprefix("service:")
            if service_name in engine.topo.services.keys():
                services.append(engine.topo.services[service_name])
                continue
            else:
                print(f"Unknown service: {service_name}")
                exit(1)
        if s in engine.topo.services.keys():
            if s in engine.topo.nodes.keys():
                print(f"Ambiguous node or service: {s} - please prepend with node: or service: to signal intention")
                exit(1)
            services.append(engine.topo.services[s])
        elif s not in engine.topo.nodes.keys():
            print(f"Neither a valid node nor service: {s}")
            exit(1)
    return services


def print_intf(name, intf, rx, tx):
    if name == intf:
        print(f"Read: {NetworkUtils.format_bytes(rx)}Bytes - Write: {NetworkUtils.format_bytes(tx)}Bytes")


if __name__ == '__main__':
    main(sys.argv[1:])
