import sys
import time

from live.engine import Engine
from network.network_utils import NetworkUtils
from topo.interface import Interface
from topo.node import Node
from topo.service import Service


def main(argv: list[str]):
    if len(argv) < 2:
        print("Script requires two or more arguments!")
        exit(1)

    engine = Engine(argv[0])
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
            print("./remote_topology.sh ping <service1> <service2>")
            exit(1)
        if argv[2] in engine.topo.services.keys():
            if argv[3] in engine.topo.services.keys():
                engine.cmd_ping(engine.topo.services[argv[2]], engine.topo.services[argv[3]], 4, handle_ping_result)
            else:
                print("No such service: " + argv[3])
                exit(1)
        else:
            print("No such service: " + argv[2])
            exit(1)
    elif argv[1].lower() == "iperf":
        if len(argv) < 4:
            print(
                "./remote_topology.sh iperf <service1> <service2> [port] [interval] [time] "
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
            if argv[3] in engine.topo.services.keys():
                engine.cmd_iperf(engine.topo.services[argv[2]], engine.topo.services[argv[3]], port, interval, time_dur,
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
            cmd = engine.cmd_ifstat(executor)
            if i.name in cmd.results:
                rx_pk, tx_pk, rx_data, tx_data, rx_err, tx_err, rx_over, tx_coll = cmd.results[i.name]
                print(f"{i.name}: rx_pk={NetworkUtils.format_thousands(rx_pk)} "
                      f"tx_pk={NetworkUtils.format_thousands(tx_pk)} "
                      f"rx_data={NetworkUtils.format_thousands(rx_data)} "
                      f"tx_data={NetworkUtils.format_thousands(tx_data)} "
                      f"rx_err={NetworkUtils.format_thousands(rx_err)} "
                      f"tx_err={NetworkUtils.format_thousands(tx_err)} "
                      f"rx_over={NetworkUtils.format_thousands(rx_over)} "
                      f"tx_coll={NetworkUtils.format_thousands(tx_coll)}")
            stop = time.time()
            time.sleep((start - stop + 10) % 1)
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


def resolve_nodes(argv: list[str], engine: Engine) -> list[Node]:
    nodes: list[Node] = []
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


def resolve_services(argv: list[str], engine: Engine) -> list[Service]:
    services: list[Service] = []
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


if __name__ == '__main__':
    main(sys.argv[1:])
