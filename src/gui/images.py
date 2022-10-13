from abc import ABC

from gui.view_utils import ViewUtils


class Images(ABC):
    router = None
    layer_3_switch = None

    @classmethod
    def load(cls):
        cls.router = ViewUtils.load_image("../res/images/router.png")
        cls.layer_3_switch = ViewUtils.load_image("../res/images/layer-3-switch.png")
