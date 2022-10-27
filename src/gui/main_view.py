import math
import threading
import time

from gui.box import Box
from gui.button import ButtonBar, Button
from gui.images import Images
from gui.view import View
from live.engine import Engine


class MainView(View):

    def __init__(self, engine: Engine, gui: 'Gui', fullscreen: bool):
        self.engine = engine
        self.gui = gui
        self.box = None
        self.active_button_bar = None

        self.gui_scale = 1.0
        self.zoom_goal = 100
        self.zoom = 1
        self.zoom_box = ButtonBar(x=10 * self.gui_scale, y=0 - 15 * self.gui_scale)
        self.zoom_box.add_button(
            Button(40 * self.gui_scale, 40 * self.gui_scale, None, "-", "Arial " + str(int(self.gui_scale * 20)),
                   on_press=lambda x, y: self.zoom_out()))
        self.zoom_factor_button = Button(80 * self.gui_scale, 40 * self.gui_scale, None,
                                         self.zoom_text(), "Arial " + str(int(self.gui_scale * 14)),
                                         on_press=None, enabled=False, text_offs_y=int((20 - 14) / 2 * self.gui_scale))
        self.zoom_box.add_button(self.zoom_factor_button)
        self.zoom_box.add_button(
            Button(40 * self.gui_scale, 40 * self.gui_scale, None, "+", "Arial " + str(int(self.gui_scale * 20)),
                   on_press=lambda x, y: self.zoom_in()))
        self.zoom_box._set_view(self)

        self.run_box = ButtonBar(x=10 * self.gui_scale, y=10 * self.gui_scale, padding=3 * self.gui_scale,
                                 margin=3 * self.gui_scale)
        self.run_box.add_button(
            Button(240 * self.gui_scale, 40 * self.gui_scale, None, "Testbed", "Arial " + str(int(self.gui_scale * 14)),
                   on_press=None))
        self.on_button = Button(40 * self.gui_scale, 40 * self.gui_scale, None, "R",
                                "Arial " + str(int(self.gui_scale * 20)),
                                on_press=lambda x, y: self.on_action(self.do_start_all))
        self.run_box.add_button(self.on_button)
        self.off_button = Button(40 * self.gui_scale, 40 * self.gui_scale, None, "S",
                                 "Arial " + str(int(self.gui_scale * 20)),
                                 on_press=lambda x, y: self.on_action(self.do_stop_all))
        self.run_box.add_button(self.off_button)
        self.destroy_button = Button(40 * self.gui_scale, 40 * self.gui_scale, None, "D",
                                     "Arial " + str(int(self.gui_scale * 20)),
                                     on_press=lambda x, y: self.on_action(self.do_destroy_all))
        self.run_box.add_button(self.destroy_button)
        self.run_box._set_view(self)

        self.select_mode = None
        self.select_callback = None

        self.message = None
        self.message_color = 'black'
        self.message_cd = 0
        self.message_fade = 0
        self.last_message = 0

        self.in_toggle = False

        self.last_scroll = 0

        self.cross = None
        self.cross_size = None

        super().__init__("Testbed", fullscreen, 200, 100)

    def set_message(self, message: str, color: str = '#000000', cd: int = 4000, fade: int = 700):
        self.message = message
        self.message_color = color
        self.message_cd = cd
        self.message_fade = fade
        self.last_message = int(time.time() * 1000)

    def set_box(self, box: Box):
        self.box = box
        # self.repaint()

    def set_select_mode(self, selectable: list[Box]):
        self.select_mode = selectable
        self.box.update_select_mode()

    def set_active_button_bar(self, button_bar: ButtonBar):
        self.active_button_bar = button_bar

    def on_resize(self, width: int, height: int):
        self.zoom_box.x = 10 * self.gui_scale
        self.zoom_box.y = height - self.zoom_box.height - 15 * self.gui_scale

    def on_paint(self):
        # Main box
        if not self.box:
            return
        self.box._set_view(self)
        self.box._set_parent(None)

        curr_zoom = float(self.zoom * 100 / self.gui_scale)
        bound = float(0.05 * 100 / self.gui_scale)
        if self.zoom_goal - bound <= curr_zoom <= self.zoom_goal + bound:
            self.zoom = self.zoom_goal * self.gui_scale / 100
        elif curr_zoom < self.zoom_goal - bound:
            self.zoom += 0.05
        elif curr_zoom > self.zoom_goal + bound:
            self.zoom -= 0.05

        min_x = self.width / self.zoom
        min_y = self.height / self.zoom
        max_x = self.gui.canvas_width
        max_y = self.gui.canvas_height

        if self.gui.main_box.x < min_x:
            self.gui.main_box.x = min_x
            self.last_scroll = time.time() * 1000
        if self.gui.main_box.y < min_y:
            self.gui.main_box.y = min_y
            self.last_scroll = time.time() * 1000
        if self.gui.main_box.x > max_x:
            self.gui.main_box.x = max_x
            self.last_scroll = time.time() * 1000
        if self.gui.main_box.y > max_y:
            self.gui.main_box.y = max_y
            self.last_scroll = time.time() * 1000

        if self.gui.main_box._dragging_anchor:
            self.last_scroll = time.time() * 1000

        self.box.on_paint(0, 0)

        if self.active_button_bar:
            self.active_button_bar.on_paint(0, 0)

        # Scroll bar (min_x/y is also the amount of pixels visible on screen
        t = time.time() * 1000
        if t - 1000 < self.last_scroll:
            perc_x = (self.gui.main_box.x - min_x) / (max_x - min_x)
            perc_y = (self.gui.main_box.y - min_y) / (max_y - min_y)
            visible_perc_x = min_x / (self.gui.canvas_width)
            visible_perc_y = min_y / (self.gui.canvas_height)
            x = (self.width - 10 * self.gui_scale) * (1 - visible_perc_x) * (1 - perc_x)
            y = self.height - self.gui_scale * 10
            w = (self.width - 10 * self.gui_scale) * visible_perc_x
            h = self.gui_scale * 5
            self.canvas.create_rectangle(x, y, x + w, y + h, fill='#A0A0A0', outline='')
            x = self.width - self.gui_scale * 10
            y = (self.height - 10 * self.gui_scale) * (1 - visible_perc_y) * (1 - perc_y)
            w = self.gui_scale * 5
            h = (self.height - 10 * self.gui_scale) * visible_perc_y
            self.canvas.create_rectangle(x, y, x + w, y + h, fill='#A0A0A0', outline='')

        # Zoom box
        self.zoom_box.on_paint(0, 0)

        # Run box
        if self.in_toggle:
            self.on_button.text = "W"
            self.off_button.text = "W"
            self.destroy_button.text = "W"
            self.on_button.enabled = False
            self.off_button.enabled = False
            self.destroy_button.enabled = False
        else:
            self.on_button.text = "R"
            self.off_button.text = "S"
            self.destroy_button.text = "D"
            self.on_button.enabled = True
            self.off_button.enabled = True
            self.destroy_button.enabled = True
        self.run_box.on_paint(0, 0)

        t = int(time.time() * 1000)
        if t - self.last_message < self.message_cd + self.message_fade:
            # We can draw something! :)
            perc = float(t - self.last_message - self.message_cd) / self.message_fade
            if perc < 0:
                perc = 0
            self.create_text(self.width / 2, self.height - 30 * self.gui_scale + (60 * self.gui_scale * perc),
                             self.message, "Arial " + str(int(15 * self.gui_scale)), fill=self.message_color)

        # Draw cross
        if self.full_screen:
            cross_width = 40
            cross_offs = 10

            cross_size = int(cross_width * self.gui_scale)
            if not self.cross or not self.cross_size or self.cross_size != cross_size:
                self.cross_size = cross_size
                self.cross = Images.get_with_size(Images.router, self.cross_size, self.cross_size)
            self.canvas.create_image(
                self.width - (cross_offs + cross_width / 2) * self.gui_scale,
                (cross_offs + cross_width / 2) * self.gui_scale,
                image=self.cross)

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        # Cross
        if self.full_screen:
            cross_width = 40
            cross_offs = 10
            if self.width - cross_width - cross_offs <= x < self.width - cross_offs \
                    and cross_offs <= y < cross_width + cross_offs:
                self.root.destroy()
                return

        if self.run_box._is_in_box(x, y):
            self.run_box.on_click(button,
                                  x - self.run_box.x,
                                  y - self.run_box.y,
                                  root_x, root_y)
            return
        if self.zoom_box._is_in_box(x, y):
            self.zoom_box.on_click(button,
                                   x - self.zoom_box.x,
                                   y - self.zoom_box.y,
                                   root_x, root_y)
            return
        if self.active_button_bar:
            if self.active_button_bar._is_in_box(x, y):
                self.active_button_bar.on_click(button,
                                                x - self.active_button_bar.x,
                                                y - self.active_button_bar.y,
                                                root_x, root_y)
                return
        x += self.gui.canvas_width * self.zoom
        y += self.gui.canvas_height * self.zoom
        self.box.on_click(button, math.floor(x / self.zoom), math.floor(y / self.zoom), root_x, root_y)

    def on_drag_begin(self, x: int, y: int, root_x: int, root_y: int):
        self.box.on_drag_begin(math.floor(x / self.zoom), math.floor(y / self.zoom), root_x, root_y)

    def on_drag_move(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        self.box.on_drag_move(math.floor(x / self.zoom), math.floor(y / self.zoom),
                              root_x, root_y,
                              math.floor(total_dx / self.zoom), math.floor(total_dy / self.zoom))

    def on_drag_end(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        self.box.on_drag_end(math.floor(x / self.zoom), math.floor(y / self.zoom),
                             root_x, root_y,
                             math.floor(total_dx / self.zoom), math.floor(total_dy / self.zoom))
        # Call mouse move to reapply cursor
        self.box.on_mouse_move(math.floor(x / self.zoom), math.floor(y / self.zoom), root_x, root_y)

    def on_mouse_move(self, x: int, y: int, root_x: int, root_y: int):
        self.box.on_mouse_move(math.floor(x / self.zoom), math.floor(y / self.zoom), root_x, root_y)

    def zoom_in(self):
        self.zoom_goal += 20
        if self.zoom_goal > 500:
            self.zoom_goal = 500
        self.zoom_factor_button.text = self.zoom_text()

    def zoom_out(self):
        self.zoom_goal -= 20
        min_zoom = math.ceil(self.gui.max_width / self.gui.canvas_width * 100)
        if self.zoom_goal < min_zoom:
            self.zoom_goal += 20
        self.zoom_factor_button.text = self.zoom_text()

    def zoom_text(self) -> str:
        return str(int(self.zoom_goal)) + "%"

    def on_action(self, callback):
        if self.in_toggle:
            return
        self.in_toggle = True
        thread = threading.Thread(target=callback)
        thread.start()
        pass

    def do_start_all(self):
        self.set_message(f"Starting all services...")
        self.engine.start_all()
        self.set_message(f"All services started")
        self.in_toggle = False

    def do_stop_all(self):
        self.set_message(f"Stopping all services...")
        self.engine.stop_all()
        self.set_message(f"All services stopped")
        self.in_toggle = False

    def do_destroy_all(self):
        self.set_message(f"Destroying all services...")
        self.engine.destroy_all()
        self.set_message(f"All services destroyed")
        self.in_toggle = False
