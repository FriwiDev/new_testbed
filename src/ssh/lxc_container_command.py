from enum import Enum

from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node


class LXCContainerStatus(Enum):
    RUNNING, STOPPED = range(2)


class LxcContainerListCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Node):
        super().__init__(target, "lxc ls")
        self.add_consumer(self)
        self.results: dict[str, LXCContainerStatus] = {}

    def on_out(self, output: str):
        split = output.split("|")
        if len(split) > 1:
            if split[5].strip() == "CONTAINER":
                if split[2].strip() == "STOPPED" or split[2].strip() == "RUNNING":
                    self.results[split[1].strip()] = LXCContainerStatus[split[2].strip()]
        pass

    def on_return(self, code: int):
        pass
