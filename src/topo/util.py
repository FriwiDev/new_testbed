import importlib
import subprocess
import typing


class MacUtil(object):

    # Method from distrinet util.py
    @classmethod
    def colon_hex(cls, val: int, bytecount: int) -> str:
        """Generate colon-hex string.
           val: input as unsigned int
           bytecount: number of bytes to convert
           returns: chStr colon-hex string"""
        pieces = []
        for i in range(bytecount - 1, -1, -1):
            piece = ((0xff << (i * 8)) & val) >> (i * 8)
            pieces.append('%02x' % piece)
        ch_str = ':'.join(pieces)
        return ch_str

    # Method from distrinet util.py
    @classmethod
    def mac_colon_hex(cls, mac: int) -> str:
        """Generate MAC colon-hex string from unsigned int.
           mac: MAC address as unsigned int
           returns: macStr MAC colon-hex string"""
        return cls.colon_hex(mac, 6)


class ClassUtil(object):

    @classmethod
    def get_class(cls, module_name: str, class_name: str) -> type:
        return getattr(importlib.import_module(module_name), class_name)

    @classmethod
    def get_class_from_dict(cls, x: dict) -> type:
        return cls.get_class(x['module'], x['class'])


class CommandUtil(object):
    @classmethod
    def run_command(cls, cmd: typing.List[str], list_output: bool = False, do_output: bool = True) -> (
    int, typing.List[str]):
        ret = []
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True)

        while True:
            output = process.stdout.readline()
            if not output.strip() == "":
                if do_output:
                    print(output.strip())
                if list_output:
                    ret.append(output.strip())
            # Do something else
            return_code = process.poll()
            if return_code is not None:
                # Process has finished, read rest of the output
                for output in process.stdout.readlines():
                    if not output.strip() == "":
                        if do_output:
                            print(output.strip())
                        if list_output:
                            ret.append(output.strip())
                return return_code, ret
