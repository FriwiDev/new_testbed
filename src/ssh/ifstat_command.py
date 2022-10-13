from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class IfstatSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Service or Node, timeout: int = 5, consumer=None):
        super().__init__(target.executor if isinstance(target, Service) else target,
                         (target.command_prefix() if isinstance(target,
                                                                Service) else "") + f"timeout {timeout} ifstat -a")
        self.add_consumer(self)
        self.interfaces: list[str] = []
        self.consumer = consumer

    def on_out(self, output: str):
        if "/" in output:
            return
        while "  " in output:
            output = output.replace("  ", " ")
        split = output.split(" ")
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
                self.consumer(self.interfaces[j], int(float(split[i]) * 1000), int(float(split[i + 1]) * 1000))
            j += 1
        pass

    def on_return(self, code: int):
        pass
