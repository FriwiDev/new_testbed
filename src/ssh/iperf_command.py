import threading
import time

from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.service import Service


class IperfSSHCommand(SSHCommand):
    def __init__(self, source: Service, target: Service, target_ip: str, port: int = 1337, interval_seconds: int = 1,
                 time_seconds: int = 10, server_options: str = "", client_options: str = "",
                 consumer=None):
        super().__init__(source.executor, "null")
        self.server = IperfServerSSHCommand(target, port, time_seconds + 3, server_options)
        self.client = IperfClientSSHCommand(source, target_ip, port, interval_seconds, time_seconds,
                                            client_options, consumer)

    def run(self):
        x = threading.Thread(target=self.server.run, args=())
        x.start()
        time.sleep(0.5)
        self.client.run()
        x.join()

    def abort(self):
        self.server.abort()
        self.client.abort()


class IperfServerSSHCommand(SSHCommand):
    def __init__(self, target: Service, port: int = 1337, time_seconds=11, server_options: str = ""):
        super().__init__(target.executor,
                         target.command_prefix() + f"timeout {time_seconds} iperf3 -s -p {port} {server_options}")


class IperfClientSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Service, ip: str, port: int = 1337, interval_seconds: int = 1,
                 time_seconds: int = 10, client_options: str = "", consumer=None):
        super().__init__(target.executor, target.command_prefix() + f"iperf3 -c {ip} -p {port} "
                                                                    f"--interval {interval_seconds} "
                                                                    f"--time {time_seconds} "
                                                                    f"--forceflush {client_options}")
        self.interval_seconds = interval_seconds
        self.consumer = consumer
        self.add_consumer(self)
        self.results: list[(int, int, int, int)] = []  # From sec, to sec, transfer bytes, transfer bandwidth (bits)

    def on_out(self, output: str):
        if not output.startswith("[") or "]" not in output:
            return
        output = output.split("]")[1]
        while "  " in output:
            output = output.replace("  ", " ")
        split = output.split(" ")
        if split[2] == "sec":
            from_sec = int(float(split[1].split("-")[0]))
            to_sec = int(float(split[1].split("-")[1]))
            transfer = float(split[3])
            transfer_unit = split[4]
            bandwidth = float(split[5])
            bandwidth_unit = split[6]
            if transfer_unit.startswith("T"):
                transfer *= 1024 * 1024 * 1024 * 1024
            elif transfer_unit.startswith("G"):
                transfer *= 1024 * 1024 * 1024
            elif transfer_unit.startswith("M"):
                transfer *= 1024 * 1024
            elif transfer_unit.startswith("K"):
                transfer *= 1024

            if bandwidth_unit.startswith("T"):
                bandwidth *= 1024 * 1024 * 1024 * 1024
            elif bandwidth_unit.startswith("G"):
                bandwidth *= 1024 * 1024 * 1024
            elif bandwidth_unit.startswith("M"):
                bandwidth *= 1024 * 1024
            elif bandwidth_unit.startswith("K"):
                bandwidth *= 1024

            if from_sec == 0 and to_sec > self.interval_seconds:
                return

            self.results.append((from_sec, to_sec, transfer, bandwidth))

            if self.consumer:
                self.consumer(from_sec, to_sec, transfer, bandwidth)
        pass

    def on_return(self, code: int):
        pass
