import signal
import subprocess

from ssh.output_consumer import OutputConsumer


class LocalCommand(object):
    def __init__(self, command: str):
        self.command = command
        self.consumers = []
        self.process = None
        self.exit_code: int or None = None

    def add_consumer(self, consumer: OutputConsumer):
        self.consumers.append(consumer)

    def run(self):
        self._exec(self.command)

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
        print("Abort!")
        if self.process:
            print("In abort...")
            self.process.send_signal(signal.SIGINT)

    def encapsule(self, cmd: str):
        return "\"" + cmd.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
