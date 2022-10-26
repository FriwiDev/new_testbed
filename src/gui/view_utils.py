from abc import ABC

from PIL import Image


class ViewUtils(ABC):
    @classmethod
    def load_image(cls, path: str) -> Image:
        return Image.open(path)
