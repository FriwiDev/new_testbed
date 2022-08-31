from abc import ABC, abstractmethod


class SSHOutputConsumer(ABC):
    @abstractmethod
    def on_out(self, output: str):
        pass

    @abstractmethod
    def on_return(self, code: int):
        pass


class PrintOutputConsumer(SSHOutputConsumer):
    def on_out(self, output: str):
        print(output)

    def on_return(self, code: int):
        pass
