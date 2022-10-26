from gui.box import Box
from gui.button import ButtonBar, Button
from gui.system_box import SystemBox
from gui.view import View


class MainView(View):

    def __init__(self, box: Box):
        self.box = box
        self.active_button_bar = None

        gui_scale = 1
        self.zoom = 100
        self.zoom_box = ButtonBar(x=10 * gui_scale, y=0 - 10 * gui_scale)
        self.zoom_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "-", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.zoom_out()))
        self.zoom_factor_button = Button(80 * gui_scale, 40 * gui_scale, None,
                                         self.zoom_text(), "Arial " + str(int(gui_scale * 14)),
                                         on_press=None, enabled=False, text_offs_y=int((20 - 14) / 2 * gui_scale))
        self.zoom_box.add_button(self.zoom_factor_button)
        self.zoom_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "+", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.zoom_in()))
        self.zoom_box._set_view(self)

        self.run_box = ButtonBar(x=10 * gui_scale, y=10 * gui_scale, padding=3, margin=3)
        self.run_box.add_button(Button(240 * gui_scale, 40 * gui_scale, None, "Testbed", "Arial " + str(int(gui_scale * 14)),
                                       on_press=None))
        self.run_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "R", "Arial " + str(int(gui_scale * 20)),
                                        on_press=lambda x, y: self.on_start_all()))
        self.run_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "S", "Arial " + str(int(gui_scale * 20)),
                                        on_press=lambda x, y: self.on_stop_all()))
        self.run_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "D", "Arial " + str(int(gui_scale * 20)),
                                       on_press=lambda x, y: self.on_destroy_all()))
        self.run_box._set_view(self)

        super().__init__("Testbed", 200, 100)

    def set_box(self, box: Box):
        self.box = box
        # self.repaint()

    def set_active_button_bar(self, button_bar: ButtonBar):
        self.active_button_bar = button_bar

    def on_resize(self, width: int, height: int):
        self.box.on_resize(width, height)
        gui_scale = 1
        self.zoom_box.x = 10 * gui_scale
        self.zoom_box.y = height - self.zoom_box.height - 10 * gui_scale

    def on_paint(self):
        self.box._set_view(self)
        self.box._set_parent(None)
        self.box.on_paint(0, 0)
        if self.active_button_bar:
            self.active_button_bar.on_paint(0, 0)
        self.zoom_box.on_paint(0, 0)
        self.run_box.on_paint(0, 0)

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        if self.run_box._is_in_box(x, y):
            self.run_box.on_click(button,
                                   x-self.run_box.x,
                                   y-self.run_box.y,
                                   root_x, root_y)
            return
        if self.zoom_box._is_in_box(x, y):
            self.zoom_box.on_click(button,
                                   x-self.zoom_box.x,
                                   y-self.zoom_box.y,
                                   root_x, root_y)
            return
        if self.active_button_bar:
            if self.active_button_bar._is_in_box(x, y):
                self.active_button_bar.on_click(button,
                                                x-self.active_button_bar.x,
                                                y-self.active_button_bar.y,
                                                root_x, root_y)
                return
        self.box.on_click(button, x, y, root_x, root_y)

    def on_drag_begin(self, x: int, y: int, root_x: int, root_y: int):
        self.box.on_drag_begin(x, y, root_x, root_y)

    def on_drag_move(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        self.box.on_drag_move(x, y, root_x, root_y, total_dx, total_dy)

    def on_drag_end(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        self.box.on_drag_end(x, y, root_x, root_y, total_dx, total_dy)
        # Call mouse move to reapply cursor
        self.box.on_mouse_move(x, y, root_x, root_y)

    def on_mouse_move(self, x: int, y: int, root_x: int, root_y: int):
        self.box.on_mouse_move(x, y, root_x, root_y)

    def zoom_in(self):
        self.zoom += 20
        if self.zoom > 500:
            self.zoom = 500
        self.zoom_factor_button.text = self.zoom_text()

    def zoom_out(self):
        self.zoom -= 20
        if self.zoom < 20:
            self.zoom = 20
        self.zoom_factor_button.text = self.zoom_text()

    def zoom_text(self) -> str:
        return str(int(self.zoom)) + "%"

    def on_start_all(self):
        pass

    def on_stop_all(self):
        pass

    def on_destroy_all(self):
        pass


def main():
    box = Box(0, 0, 100, 100)
    box.draggable = False
    box.resizeable = False
    box1 = Box(50, 50, 200, 200)
    box2 = Box(300, 50, 200, 200)
    system_box = SystemBox(500, 500, 500, 500)
    system_box.available_bounding_boxes = [(0, 0, 1920, 1080, 0)]
    system_box.current_box = (0, 0, 1920, 1080, 0)
    interface_box = Box(0, 0, 100, 50)
    system_box.add_interface_box(interface_box, True)
    box1.available_bounding_boxes = [(50, 50, 300, 300, 0), (100, 400, 300, 300, 0)]
    box1.current_box = (50, 50, 300, 300, 0)
    box2.available_bounding_boxes = [(0, 0, 1920, 1080, 0)]
    box2.current_box = (0, 0, 1920, 1080, 0)
    box.add_box(box1)
    box.add_box(box2)
    box.add_box(system_box)
    box1.lines.append(
        (box2, (4, 2), [Box.NORTH, Box.WEST, Box.SOUTH, Box.EAST], [Box.NORTH, Box.WEST, Box.SOUTH, Box.EAST]))
    view = MainView(box)
    view.run_ui_loop()


if __name__ == '__main__':
    main()
