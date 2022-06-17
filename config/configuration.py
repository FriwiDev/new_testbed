class Command(object):
    def __init__(self, cmd: str = None):
        self.cmd = cmd

    def to_str(self) -> str:
        if self.cmd is None:
            return ""
        return self.cmd


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
        self.start_cmds: list[Command] = []
        self.stop_cmds: list[Command] = []
        self.files: list[File] = []
        self.start_instructions: list[Instruction] = []
        self.stop_instructions: list[Instruction] = []

    def add_command(self, start_cmd: Command, stop_cmd: Command):
        self.start_cmds.append(start_cmd)
        self.stop_cmds.append(stop_cmd)

    def add_file(self, file: File):
        self.files.append(file)

    def add_instruction(self, start_instruction: Instruction, stop_instruction: Instruction):
        self.start_instructions.append(start_instruction)
        self.stop_instructions.append(stop_instruction)
