from typing import Dict


class GuiDataAttachment(object):
    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.debug = False
        self.stat_data = []

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height, "stat_data": self.stat_data,
                "debug": self.debug}

    @classmethod
    def from_dict(cls, input: dict) -> 'GuiDataAttachment':
        ret = GuiDataAttachment(int(input['x']), int(input['y']), int(input['width']), int(input['height']))
        if "stat_data" in input.keys():
            ret.stat_data = [x for x in input['stat_data']]
        if "debug" in input.keys():
            ret.debug = bool(input['debug'])
        return ret
