import subprocess

from ssh.ssh_output_consumer import SSHOutputConsumer
from topo.node import Node


# TODO Do not require SSH Server on local node
class SSHCommand(object):
    def __init__(self, node: Node, command: str):
        self.node = node
        self.command = command
        self.consumers = []
        self.process = None
        self.exit_code: int or None = None

    def add_consumer(self, consumer: SSHOutputConsumer):
        self.consumers.append(consumer)

    def run(self):
        cmd = "("
        if self.node.ssh_work_dir and self.node.ssh_work_dir != "":
            cmd += f"echo \" cd \\\"{self.node.ssh_work_dir}\\\" && "
        cmd += "echo \"" + self.command.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
        cmd += ") | " + self.node.get_ssh_base_command() + " \"/bin/bash\""
        # print(cmd)
        self._exec(cmd)

        # Does not work :(
        # inner = ""
        # if self.node.ssh_work_dir and self.node.ssh_work_dir != "":
        #    inner += f"cd \"{self.node.ssh_work_dir}\" && "
        # inner += self.command
        # inner1 = "/bin/bash -c " + self.encapsule(inner)
        # cmd = self.node.get_ssh_base_command() + " " + self.encapsule(inner1)
        # self._exec(cmd)

    def _exec(self, cmd: str):
        self.process = subprocess.Popen(cmd,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        universal_newlines=True)

        while True:
            output = self.process.stdout.readline().strip()
            if not output == "":
                for consumer in self.consumers:
                    consumer.on_out(output)
            # Do something else
            return_code = self.process.poll()
            if return_code is not None:
                # Process has finished, read rest of the output
                for output in self.process.stdout.readlines():
                    output = output.strip()
                    if not output == "":
                        for consumer in self.consumers:
                            consumer.on_out(output)
                self.exit_code = return_code
                for consumer in self.consumers:
                    consumer.on_return(return_code)
                return

    def abort(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def encapsule(self, cmd: str):
        return "\"" + cmd.replace("\\", "\\\\").replace("\"", "\\\"") + "\""


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
