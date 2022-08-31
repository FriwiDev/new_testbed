import sys

from config.export.ssh_exporter import SSHConfigurationExporter
from topo.topo import TopoUtil


def main(argv: list[str]):
    if len(argv) < 2:
        print("Script requires two or more arguments!")
        exit(1)

    topo = TopoUtil.from_file(argv[0])

    if len(argv) == 2:
        if "all" in argv[1].lower():
            to_work = topo.nodes.keys()
        else:
            to_work = topo.services.keys()
    else:
        to_work = []
        for i in range(2, len(argv)):
            to_work.append(argv[i])

    if argv[1].lower() == "start_all":
        nodes = []
        for name in to_work:
            if name not in topo.nodes.keys():
                print("Unknown node: " + name)
                exit(1)
            nodes.append(topo.nodes[name])
        for node in nodes:
            config = node.get_configuration_builder(topo).build()
            exporter = SSHConfigurationExporter(config, node)
            exporter.start_all(topo)
    elif argv[1].lower() == "stop_all":
        nodes = []
        for name in to_work:
            if name not in topo.nodes.keys():
                print("Unknown node: " + name)
                exit(1)
            nodes.append(topo.nodes[name])
        for node in nodes:
            config = node.get_configuration_builder(topo).build()
            exporter = SSHConfigurationExporter(config, node)
            exporter.stop_all(topo)
    elif argv[1].lower() == "start":
        services = []
        for name in to_work:
            if name not in topo.services.keys():
                print("Unknown service: " + name)
                exit(1)
            services.append(topo.services[name])
        for service in services:
            print(f">>> Starting {service.name}")
            builder = service.executor.get_configuration_builder(topo)
            config = builder.build()
            exporter = SSHConfigurationExporter(config, service.executor)
            exporter.start(topo, builder, service)
    elif argv[1].lower() == "stop":
        services = []
        for name in to_work:
            if name not in topo.services.keys():
                print("Unknown service: " + name)
                exit(1)
            services.append(topo.services[name])
        for service in services:
            print(f">>> Stopping {service.name}")
            builder = service.executor.get_configuration_builder(topo)
            config = builder.build()
            exporter = SSHConfigurationExporter(config, service.executor)
            exporter.stop(topo, builder, service)
    else:
        print("Unknown action " + argv[1])
        exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
