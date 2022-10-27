from abc import ABC, abstractmethod
from tkinter import Frame, Tk, BOTH, Canvas, Menu, PhotoImage, Button

from gui.images import Images


class View(ABC):
    root = Tk()
    Images.load()
    root.tk.call('wm', 'iconphoto', root._w, Images.router_icon)

    def __init__(self, title: str, fullscreen: bool, width: int, height: int):
        if fullscreen:
            View.root.attributes("-fullscreen", True)
            self.frame = Frame(master=View.root)
        else:
            self.frame = Frame(master=View.root, width=width, height=height)
        self.popup_menu: Menu = None
        self.set_title(title)
        self.width = width
        self.height = height
        self.frame.pack(fill=BOTH, expand=1)

        self.canvas = Canvas(self.frame, bg='white')
        self.on_paint()

        self._bind()

        self.canvas.pack(fill=BOTH, expand=1)

        # Drag n drop
        self._pressed: tuple[int, int, int, int] = None
        self._moved = False

    @abstractmethod
    def on_resize(self, width: int, height: int):
        pass

    @abstractmethod
    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        pass

    @abstractmethod
    def on_mouse_move(self, x: int, y: int, root_x: int, root_y: int):
        pass

    @abstractmethod
    def on_paint(self):
        pass

    @abstractmethod
    def on_drag_begin(self, x: int, y: int, root_x: int, root_y: int):
        pass

    @abstractmethod
    def on_drag_move(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        pass

    @abstractmethod
    def on_drag_end(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        pass

    def repaint(self):
        self.canvas.delete("all")
        self.on_paint()
        self.canvas.update()
        self.root.after(15, self.repaint)

    def close(self):
        self._unbind()
        self.frame.destroy()

    def set_title(self, title: str):
        self.frame.winfo_toplevel().title(title)

    def create_text(self, x: float or int, y: float or int, text: str, font: str = "Arial 12", angle: int = 0,
                    fill: str = "black", anchor: str = "center", justify: str = "center") -> tuple[int, int, int, int]:
        t = self.canvas.create_text(x, y, text=text, font=font, angle=angle, fill=fill, anchor=anchor, justify=justify)
        return self.canvas.bbox(t)

    def _bind(self):
        self.width, self.height = self.canvas.winfo_width(), self.canvas.winfo_height()
        self._func_id_resize = self.canvas.bind("<Configure>", self._resize)
        self._func_id_button2 = self.canvas.bind("<Button-2>", lambda evt: self._click(2, evt))
        self._func_id_button3 = self.canvas.bind("<Button-3>", lambda evt: self._click(3, evt))
        self._func_id_button1_press = self.canvas.bind("<ButtonPress-1>", self._b1_press)
        self._func_id_button1_motion = self.canvas.bind("<B1-Motion>", self._b1_motion)
        self._func_id_button1_release = self.canvas.bind("<ButtonRelease-1>", self._b1_release)
        self._func_id_mouse_move = self.canvas.bind("<Motion>", self._mouse_move)

    def _unbind(self):
        if self._func_id_resize:
            self.canvas.unbind("<Configure>", self._func_id_resize)
            self._func_id_resize = None
        if self._func_id_button2:
            self.canvas.unbind("<Button-2>", self._func_id_button2)
            self._func_id_button2 = None
        if self._func_id_button3:
            self.canvas.unbind("<Button-3>", self._func_id_button3)
            self._func_id_button3 = None
        if self._func_id_button1_press:
            self.canvas.unbind("<ButtonPress-1>", self._func_id_button1_press)
            self._func_id_button1_press = None
        if self._func_id_button1_motion:
            self.canvas.unbind("<B1-Motion>", self._func_id_button1_motion)
            self._func_id_button1_motion = None
        if self._func_id_button1_release:
            self.canvas.unbind("<ButtonRelease-1>", self._func_id_button1_release)
            self._func_id_button1_release = None
        if self._func_id_mouse_move:
            self.canvas.unbind("<Motion>", self._func_id_mouse_move)
            self._func_id_mouse_move = None

    def _resize(self, event):
        if (event.widget == self.canvas and
                (self.width != event.width or self.height != event.height)):
            self.width, self.height = event.width, event.height
            self.on_resize(self.width, self.height)

    def _click(self, button: int, event):
        if event.widget == self.canvas:
            if self.popup_menu:
                self.popup_menu.destroy()
            self.on_click(button, event.x, event.y, event.x_root, event.y_root)

    def _b1_press(self, event):
        self._pressed = event.x, event.y, event.x_root, event.y_root

    def _b1_motion(self, event):
        x, y, x_root, y_root = self._pressed
        if not self._moved:
            self.on_drag_begin(x, y, x_root, y_root)
            self._moved = True
        self.on_drag_move(event.x, event.y, event.x_root, event.y_root, event.x - x, event.y - y)

    def _b1_release(self, event):
        if self._moved:
            self._moved = False
            x, y, x_root, y_root = self._pressed
            self.on_drag_end(event.x, event.y, event.x_root, event.y_root, event.x - x, event.y - y)
        else:
            self._click(1, event)
        self._pressed = None

    def _mouse_move(self, event):
        self.on_mouse_move(event.x, event.y, event.x_root, event.y_root)

    def show_popup(self, x: int, y: int, elements: list[str], callback, images: list[PhotoImage] = None):
        if self.popup_menu:
            self.popup_menu.destroy()
        self.popup_menu = Menu(self.frame, tearoff=0)
        for i in range(0, len(elements)):
            image = None if not images or len(images) <= i else images[i]
            if elements[i]:
                self.popup_menu.add_command(label=elements[i],
                                            image=image,
                                            compound='left',
                                            command=lambda j=i: self._popup_callback(j, elements[j], callback))
            else:
                self.popup_menu.add_separator()
        try:
            self.popup_menu.tk_popup(x, y, 0)
        finally:
            self.popup_menu.grab_release()

    def _popup_callback(self, num: int, name: str, callback):
        self.popup_menu.destroy()
        self.popup_menu = None
        callback(num, name)

    def add_button(self, x: int, y: int, label: str, image: PhotoImage = None, callback=None) -> Button:
        ret = Button(self.canvas, text=label, image=image, compound='left', command=callback)
        ret.place(x=x, y=y)
        return ret

    def set_cursor(self, cursor: str):
        self.canvas.config(cursor=cursor)

    def run_ui_loop(self):
        self.root.after(100, self.repaint)
        self.root.mainloop()
