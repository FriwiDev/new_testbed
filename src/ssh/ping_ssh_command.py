import ipaddress

from ssh.ssh_command import SSHCommand
from ssh.ssh_output_consumer import SSHOutputConsumer
from ssh.string_util import StringUtil
from topo.service import Service


class PingSSHCommand(SSHCommand, SSHOutputConsumer):
    def __init__(self, service: Service, target: ipaddress.ip_address, count: int or None = 4):
        count_str = ""
        if count is not None:
            count_str = f"-c {str(count)}"
        super().__init__(service.executor, service.command_prefix() + f"ping {count_str} {str(target)}")
        self.add_consumer(self)
        self.ping_results: dict[int, (str or (int, float))] = {}
        self.packets_transmitted: int or None = None
        self.packets_received: int or None = None
        self.time: int or None = None
        self.min: float or None = None
        self.avg: float or None = None
        self.max: float or None = None
        self.mdev: float or None = None

    def on_out(self, output: str):
        args = output.split()
        if "icmp_seq=" in output:
            # New ping result
            icmp_seq = int(StringUtil.get_argument_starting_with(args, "icmp_seq="))
            if "ttl=" in output:
                # Successful ping result
                ttl = int(StringUtil.get_argument_starting_with(args, "ttl="))
                time = float(StringUtil.get_argument_starting_with(args, "time="))
                self.ping_results[icmp_seq] = (ttl, time)
            else:
                # Not successful ping result
                reason = output.split(f"icmp_seq={icmp_seq}")[1].strip()
                self.ping_results[icmp_seq] = reason
        elif "packets transmitted" in output:
            self.packets_transmitted = int(args[0])
            self.packets_received = int(args[3])
            self.time = int(args[StringUtil.get_index_of(args, "time") + 1].removesuffix("ms"))
        elif output.startswith("rtt"):
            values = args[3].split("/")
            self.min = float(values[0])
            self.avg = float(values[1])
            self.max = float(values[2])
            self.mdev = float(values[3])
        pass

    def on_return(self, code: int):
        pass
