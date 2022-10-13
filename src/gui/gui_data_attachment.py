class GuiDataAttachment(object):
    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, input: dict) -> 'GuiDataAttachment':
        return GuiDataAttachment(int(input['x']), int(input['y']), int(input['width']), int(input['height']))
