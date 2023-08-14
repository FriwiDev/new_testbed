import sys

from ssh.output_consumer import PrintOutputConsumer
from ssh.ssh_command import SSHCommand
from topo.topo import TopoUtil


def main(argv: typing.List[str]):
    if len(argv) < 3:
        print("Script requires at least three arguments!")
        exit(1)

    topo = TopoUtil.from_file(argv[0])

    if not argv[1] in topo.services.keys():
        print(f"Execution target must be a valid service name! {argv[1]} not found!")
        exit(1)

    service = topo.services[argv[1]]

    cmd = service.command_prefix() + "\"" + argv[2].replace("\\", "\\\\").replace("\"", "\\\"") + "\""

    for i in range(3, len(argv)):
        cmd += " \"" + argv[i].replace("\\", "\\\\").replace("\"", "\\\"") + "\""

    print(f"Executing command on {service.executor.name}: {cmd}")

    command = SSHCommand(service.executor, cmd)
    command.add_consumer(PrintOutputConsumer())
    command.run()

    exit(command.exit_code)


if __name__ == '__main__':
    main(sys.argv[1:])
