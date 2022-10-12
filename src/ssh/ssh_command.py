from ssh.localcommand import LocalCommand
from topo.node import Node


# TODO Do not require SSH Server on local node
class SSHCommand(LocalCommand):
    def __init__(self, node: Node, command: str):
        super().__init__(command)
        self.node = node

    def run(self):
        cmd = "("
        if self.node.ssh_work_dir and self.node.ssh_work_dir != "":
            cmd += f"echo \" cd \\\"{self.node.ssh_work_dir}\\\"\" && "
        cmd += "echo \"" + self.command.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
        cmd += ") | " + self.node.get_ssh_base_command() + " \"/bin/bash\""
        # print(cmd)
        self._exec(cmd)


class FileSendCommand(SSHCommand):
    def __init__(self, node: Node, prefix: str, src: str, dst: str):
        super().__init__(node, "")
        self.prefix = prefix
        self.src = src
        self.dst = dst

    def run(self):
        inner = f"cat > \""
        if self.node.ssh_work_dir and self.node.ssh_work_dir != "":
            inner += f"{self.node.ssh_work_dir}/"
        inner += f"{self.dst}\""
        inner1 = f"{self.prefix} /bin/bash -c " + self.encapsule(inner)
        cmd = f"cat \"{self.src}\" | {self.node.get_ssh_base_command()} " + self.encapsule(inner1)
        self._exec(cmd)
