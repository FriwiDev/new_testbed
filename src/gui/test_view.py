from gui.images import Images
from gui.view import View


class TestView(View):
    def __init__(self):
        self.image = Images.layer_3_switch
        super().__init__("Testbed", 200, 100)
        self.button1 = self.add_button(0, 0, "Testbutton", self.image, lambda: self.button1.destroy())

    def on_resize(self, width: int, height: int):
        # self.repaint()
        pass

    def on_paint(self):
        offsx = self.width / 2 - 200
        offsy = self.height / 2 - 150
        self.canvas.create_line(offsx + 15, offsy + 25, offsx + 200, offsy + 25)
        self.canvas.create_line(offsx + 300, offsy + 35, offsx + 300, offsy + 200, dash=(4, 2))
        self.canvas.create_line(offsx + 55, offsy + 85, offsx + 155, offsy + 85, offsx + 105, offsy + 180, offsx + 55,
                                offsy + 85)
        bbox = self.create_text(offsx + 200, offsy, text="Hello world", font="Arial 17", angle=270, fill='green')
        self.canvas.create_image((offsx, offsy), image=self.image)
        self.canvas.create_rectangle(bbox, outline='red')

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        print(f"Received click {button} on {x}:{y}")
        if button == 3:
            self.show_popup(root_x, root_y, ["Hello", "World"], self.on_popup_pressed,
                            [Images.router, Images.layer_3_switch])

    def on_drag_begin(self, x: int, y: int, root_x: int, root_y: int):
        print(f"Drag begin {x}:{y}")

    def on_drag_move(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        print(f"Drag move {x}:{y} with total delta {total_dx}:{total_dy}")

    def on_drag_end(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        print(f"Drag end {x}:{y} with total delta {total_dx}:{total_dy}")

    def on_popup_pressed(self, ind: int, name: str):
        print(f"Pressed popup element {name} at {str(ind)}")

    def on_mouse_move(self, x: int, y: int, root_x: int, root_y: int):
        pass


def main():
    TestView()
    View.run_ui_loop()


if __name__ == '__main__':
    main()
