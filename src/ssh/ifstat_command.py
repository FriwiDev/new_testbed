from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class IfstatSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Service or Node):
        super().__init__(target.executor if isinstance(target, Service) else target,
                         (target.command_prefix() if isinstance(target, Service) else "") + "ifstat --interval=1")
        self.add_consumer(self)
        # intf name, rx pkts, tx pkts, rx data, tx data, rx err, tx err, rx over, tx coll
        self.results: dict[str, (int, int, int, int, int, int, int, int)] = {}
        self.current_interface: (str, int, int, int, int) or None = None

    def on_out(self, output: str):
        if output.startswith("#") or "/" in output:
            return
        while "  " in output:
            output = output.replace("  ", " ")
        split = output.split(" ")
        if self.current_interface:
            self.results[self.current_interface[0]] = (self.current_interface[1],
                                                       self.current_interface[2],
                                                       self.current_interface[3],
                                                       self.current_interface[4],
                                                       self.parse(split[0]),
                                                       self.parse(split[2]),
                                                       self.parse(split[4]),
                                                       self.parse(split[6]))
            self.current_interface = None
        else:
            self.current_interface = (split[0],
                                      self.parse(split[1]),
                                      self.parse(split[3]),
                                      self.parse(split[5]),
                                      self.parse(split[7]))
        pass

    def parse(self, arg: str) -> int:
        if arg.endswith("K"):
            return int(arg.removesuffix("K")) * 1000
        if arg.endswith("M"):
            return int(arg.removesuffix("M")) * 1000 * 1000
        if arg.endswith("G"):
            return int(arg.removesuffix("G")) * 1000 * 1000 * 1000
        if arg.endswith("T"):
            return int(arg.removesuffix("T")) * 1000 * 1000 * 1000 * 1000
        return int(arg)

    def on_return(self, code: int):
        pass
