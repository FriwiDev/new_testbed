from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class LockReadSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Node, dir: str, file: str):
        super().__init__(target, f"mkdir -p {dir} && flock {dir}/{file} cat {dir}/{file}")
        self.add_consumer(self)
        self.content: str = ""

    def on_out(self, output: str):
        self.content += output + "\n"

    def on_return(self, code: int):
        pass
