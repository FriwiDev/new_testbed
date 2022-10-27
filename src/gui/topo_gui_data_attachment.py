class TopoGuiDataAttachment(object):
    def __init__(self, x: int = -1, y: int = -1, zoom: int = 100):
        self.x = x
        self.y = y
        self.zoom = zoom

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "zoom": self.zoom}

    @classmethod
    def from_dict(cls, input: dict) -> 'TopoGuiDataAttachment':
        ret = TopoGuiDataAttachment(int(input['x']), int(input['y']), int(input['zoom']))
        return ret
