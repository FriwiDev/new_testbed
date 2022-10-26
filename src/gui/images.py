import tkinter
from abc import ABC

from PIL import Image
from PIL.ImageTk import PhotoImage

from gui.view_utils import ViewUtils


class Images(ABC):
    router_icon: tkinter.PhotoImage = None
    router: Image = None
    layer_3_switch: Image = None

    @classmethod
    def load(cls):
        cls.router_icon = tkinter.PhotoImage("../res/images/router.png")

        cls.router = ViewUtils.load_image("../res/images/router.png")
        cls.layer_3_switch = ViewUtils.load_image("../res/images/layer-3-switch.png")

    @classmethod
    def get_with_size(cls, img: Image, x: int = -1, y: int = -1) -> PhotoImage:
        if x == -1:
            x = img.width()
        if y == -1:
            y = img.height()
        return PhotoImage(img.resize((x, y), Image.ANTIALIAS))
