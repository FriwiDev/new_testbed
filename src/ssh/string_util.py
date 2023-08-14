import typing


class StringUtil(object):
    @classmethod
    def get_argument_starting_with(cls, args: typing.List[str], prefix: str) -> str:
        for arg in args:
            if arg.startswith(prefix):
                return arg[len(prefix):]
        return None

    @classmethod
    def get_index_of(cls, args: typing.List[str], check: str) -> int:
        ret = 0
        for arg in args:
            if arg == check:
                return ret
            ret += 1
        return None

    @classmethod
    def remove_suffix(cls, s: str, suffix: str):
        if s.endswith(suffix):
            return s[:len(s)-len(suffix)]
        else:
            return s

    @classmethod
    def remove_prefix(cls, s: str, prefix: str):
        if s.startswith(prefix):
            return s[len(prefix):]
        else:
            return s
