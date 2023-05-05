from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class LockWriteSSHCommand(SSHCommand):
    def __init__(self, node: Node, dir: str, file: str, local: str):
        super().__init__(node, "")
        self.prefix = ""
        self.dir = dir
        self.file = file
        self.local = local

    def run(self):
        inner = f"cat > \"{self.dir}/{self.file}\""
        inner1 = f"{self.prefix} mkdir -p {self.dir} && flock {self.dir}/{self.file} /bin/bash -c " + self.encapsule(inner)
        cmd = f"cat \"{self.local}\" | {self.node.get_ssh_base_command()} " + self.encapsule(inner1)
        self._exec(cmd)
