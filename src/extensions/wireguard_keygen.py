from ssh.localcommand import LocalCommand
from ssh.output_consumer import FunctionOutputConsumer


class WireguardKeygen(object):
    def __init__(self):
        self.private_key = None
        self.public_key = None

    def gen_keys(self):
        cmd = LocalCommand("wg genkey")
        cmd.add_consumer(FunctionOutputConsumer(self.set_priv_key, self.check_return_value))
        cmd.run()
        cmd = LocalCommand(f"echo \"{self.private_key}\" | wg pubkey")
        cmd.add_consumer(FunctionOutputConsumer(self.set_pub_key, self.check_return_value))
        cmd.run()

    def set_priv_key(self, key: str):
        self.private_key = key

    def set_pub_key(self, key: str):
        self.public_key = key

    def check_return_value(self, code: int):
        if code != 0:
            raise Exception("wg command returned code " + str(code))
