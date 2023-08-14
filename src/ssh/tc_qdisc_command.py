import typing
from typing import Dict

from ssh.output_consumer import OutputConsumer
from ssh.ssh_command import SSHCommand
from topo.node import Node
from topo.service import Service


class TcQdiscSSHCommand(SSHCommand, OutputConsumer):
    def __init__(self, target: Service or Node):
        super().__init__(target.executor if isinstance(target, Service) else target,
                         (target.command_prefix() if isinstance(target,
                                                                Service) else "") + f"tc qdisc")
        self.add_consumer(self)
        # Dev name, delay, delay_variation, delay_correlation, loss, loss_correlation
        self.results: Dict[str, (int, int, float, float, float)] = {}

    def on_out(self, output: str):
        while "  " in output:
            output = output.replace("  ", " ")
        split = output.split(" ")
        dev = split[4]
        if split[1] == "netem":
            delay_ind = self.find_ind(5, "delay", split)
            loss_ind = self.find_ind(5, "loss", split)
            l = len(split)

            delay = 0
            delay_variation = 0
            delay_correlation = 0.0
            loss = 0.0
            loss_correlation = 0.0

            if delay_ind != -1:
                if delay_ind + 1 < l:
                    delay = self.parse_micro_seconds(split[delay_ind + 1])
                    if delay > 0 and delay_ind + 2 < l:
                        delay_variation = self.parse_micro_seconds(split[delay_ind + 2])
                        if delay_variation > 0 and delay_ind + 3 < l:
                            delay_correlation = self.parse_percent(split[delay_ind + 3])

            if loss_ind != -1:
                if loss_ind + 1 < l:
                    loss = self.parse_percent(split[loss_ind + 1])
                    if loss > 0 and loss_ind + 2 < l:
                        loss_correlation = self.parse_percent(split[loss_ind + 2])

            self.results[dev] = (delay, delay_variation, delay_correlation, loss, loss_correlation)
        else:
            # We cannot work with this type of qdisc
            self.results[dev] = (0, 0, 0, 0, 0)
        pass

    def on_return(self, code: int):
        pass

    def parse_micro_seconds(self, arg: str) -> int:
        if arg.endswith("us"):
            return int(float(arg.removesuffix("us")))
        if arg.endswith("ms"):
            return int(float(arg.removesuffix("ms")) * 1000)
        if arg.endswith("s"):
            return int(float(arg.removesuffix("s")) * 1000 * 1000)
        if not arg.replace(".", "").isdigit():
            return 0
        return int(float(arg))

    def parse_percent(self, arg: str) -> float:
        if arg.endswith("%"):
            return float(arg.removesuffix("%")) / 100
        if not arg.replace(".", "").isdigit():
            return 0
        return float(arg)

    def find_ind(self, ind: int, arg: str, li: typing.List[str]) -> int:
        for i in range(ind, len(li)):
            if li[i] == arg:
                return i
        return -1
