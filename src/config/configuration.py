from os import PathLike
from typing import Dict


class Command(object):
    def __init__(self, cmd: str = None):
        self.cmd = cmd

    def to_str(self) -> str:
        if self.cmd is None:
            return ""
        return self.cmd

    def __eq__(self, other):
        return self.cmd == other.cmd


class File(object):
    def __init__(self, name: str):
        self.name = name
        self.content = ""

    def append(self, content: str):
        self.content += content

    def to_str(self) -> str:
        return self.content


class Instruction(object):
    # TODO Research what is actually needed for a key press
    def __init__(self, key_press: str):
        self.key_press = key_press

    def to_str(self) -> str:
        return self.key_press


class Configuration(object):
    def __init__(self):
        self.start_cmds: typing.List[Command] = []
        self.stop_cmds: typing.List[Command] = []
        self.files: Dict[str, typing.List[(PathLike, PathLike)]] = {}
        self.start_instructions: typing.List[Instruction] = []
        self.stop_instructions: typing.List[Instruction] = []

    def add_command(self, start_cmd: Command, stop_cmd: Command):
        self.start_cmds.append(start_cmd)
        self.stop_cmds.append(stop_cmd)

    def add_file(self, service: 'Service', file: PathLike, dst: PathLike):
        if service.name not in self.files.keys():
            self.files[service.name] = [(file, dst)]
            return
        self.files[service.name].append((file, dst))

    def add_instruction(self, start_instruction: Instruction, stop_instruction: Instruction):
        self.start_instructions.append(start_instruction)
        self.stop_instructions.append(stop_instruction)
