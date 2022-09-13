from abc import ABC, abstractmethod


class OutputConsumer(ABC):
    @abstractmethod
    def on_out(self, output: str):
        pass

    @abstractmethod
    def on_return(self, code: int):
        pass


class PrintOutputConsumer(OutputConsumer):
    def on_out(self, output: str):
        print(output)

    def on_return(self, code: int):
        pass


class FunctionOutputConsumer(OutputConsumer):
    def __init__(self, outfun=None, retfun=None):
        self.outfun = outfun
        self.retfun = retfun

    def on_out(self, output: str):
        if self.outfun:
            self.outfun(output)

    def on_return(self, code: int):
        if self.retfun:
            self.retfun(code)
