import typing

from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class IfstatSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Service or Node, timeout: int = 5, consumer=None):
        super().__init__(target.executor if isinstance(target, Service) else target,
                         (target.command_prefix() if isinstance(target,
                                                                Service) else "") + f"timeout {timeout} ifstat")
        self.add_consumer(self)
        self.interfaces: typing.List[str] = []
        self.consumer = consumer
        self.old_ifstat = False

    def on_out(self, output: str):
        if "/" in output:
            if "Interface " in output:
                self.old_ifstat = True
            return
        while "  " in output:
            output = output.replace("  ", " ")
        split = output.split(" ")

        if self.old_ifstat:
            if len(split[0]) > 0:
                intf = split[0]
                rx = self.parse(split[5])
                tx = self.parse(split[7])
                self.consumer(intf, rx * 8, tx * 8)
        else:
            if len(self.interfaces) == 0:
                for s in split:
                    if not len(s) == 0:
                        self.interfaces.append(s)
                return
            j = 0
            for i in range(0, len(split)):
                if i % 2 == 1:
                    continue
                # intf name, in bytes, out bytes
                if self.consumer:
                    self.consumer(self.interfaces[j], int(float(split[i]) * 1000) * 8,
                                  int(float(split[i + 1]) * 1000) * 8)
                j += 1
        pass

    def on_return(self, code: int):
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
