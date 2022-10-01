from gui.box import Box
from gui.system_box import SystemBox
from gui.view import View


class MainView(View):

    def __init__(self, box: Box):
        self.box = box
        super().__init__("Testbed", 200, 100)

    def set_box(self, box: Box):
        self.box = box
        self.repaint()

    def on_resize(self, width: int, height: int):
        self.box.on_resize(width, height)
        self.repaint()

    def on_paint(self):
        self.box._set_view(self)
        self.box._set_parent(None)
        self.box.on_paint(0, 0)

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
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
    MainView(box)
    View.run_ui_loop()


if __name__ == '__main__':
    main()
