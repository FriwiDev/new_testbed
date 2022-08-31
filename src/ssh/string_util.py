class StringUtil(object):
    @classmethod
    def get_argument_starting_with(cls, args: list[str], prefix: str) -> str:
        for arg in args:
            if arg.startswith(prefix):
                return arg[len(prefix):]
        return None

    @classmethod
    def get_index_of(cls, args: list[str], check: str) -> int:
        ret = 0
        for arg in args:
            if arg == check:
                return ret
            ret += 1
        return None
