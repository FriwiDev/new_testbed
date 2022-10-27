import tkinter
from abc import ABC

from PIL import Image
from PIL.ImageTk import PhotoImage

from gui.view_utils import ViewUtils


class Images(ABC):
    router_icon: tkinter.PhotoImage = None
    router: Image = None

    close: Image = None
    destroy: Image = None
    iperf_disabled: Image = None
    iperf_enabled: Image = None
    ping_disabled: Image = None
    ping_enabled: Image = None
    run: Image = None
    rx: Image = None
    stop: Image = None
    tx: Image = None
    wait: Image = None

    @classmethod
    def load(cls):
        cls.router_icon = tkinter.PhotoImage("../res/images/router.png")

        cls.router = ViewUtils.load_image("../res/images/router.png")

        cls.close = ViewUtils.load_image("../res/images/close.png")
        cls.destroy = ViewUtils.load_image("../res/images/destroy.png")
        cls.info = ViewUtils.load_image("../res/images/info.png")
        cls.iperf_disabled = ViewUtils.load_image("../res/images/iperf_disabled.png")
        cls.iperf_enabled = ViewUtils.load_image("../res/images/iperf_enabled.png")
        cls.ping_disabled = ViewUtils.load_image("../res/images/ping_disabled.png")
        cls.ping_enabled = ViewUtils.load_image("../res/images/ping_enabled.png")
        cls.run = ViewUtils.load_image("../res/images/run.png")
        cls.rx = ViewUtils.load_image("../res/images/rx.png")
        cls.stop = ViewUtils.load_image("../res/images/stop.png")
        cls.tx = ViewUtils.load_image("../res/images/tx.png")
        cls.wait = ViewUtils.load_image("../res/images/wait.png")

    @classmethod
    def get_with_size(cls, img: Image, x: int = -1, y: int = -1) -> PhotoImage:
        if x == -1:
            x = img.width()
        if y == -1:
            y = img.height()
        return PhotoImage(img.resize((int(x), int(y)), Image.ANTIALIAS))
