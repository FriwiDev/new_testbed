from abc import ABC
from tkinter import PhotoImage


class ViewUtils(ABC):
    @classmethod
    def load_image(cls, path: str) -> PhotoImage:
        return PhotoImage(file=path)
