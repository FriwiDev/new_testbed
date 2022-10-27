from tkinter import PhotoImage

from gui.box import Box


class Button(object):
    def __init__(self, width: int, height: int, image: PhotoImage = None, text: str = None,
                 font: str = None, fill: str = 'white', foreground: str = 'black', on_press=None, enabled: bool = True,
                 text_offs_y: int = 0):
        self.image = image
        self.text = text
        self.font = font
        self.x = 0
        self.y = 0
        self.width = width
        self.height = height
        self.fill = fill
        self.foreground = foreground
        self.on_press = on_press
        self.enabled = enabled
        self.text_offs_y = text_offs_y
        self.disabled_fill = '#C0C0C0'

    def _set_view(self, view: 'View'):
        self.view = view

    def on_paint(self, offs_x: int, offs_y: int):
        abs_x = self.x + offs_x
        abs_y = self.y + offs_y
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.width, abs_y + self.height,
                                          fill=self.fill if self.enabled else self.disabled_fill)
        if self.image:
            img_x = abs_x + self.width / 2 - self.image.width() / 2
            img_y = abs_y + self.height / 2 - self.image.height() / 2
            self.view.canvas.create_image((img_x, img_y), image=self.image)
        elif self.text:
            if not self.font:
                self.font = "Arial 12"
            self.view.create_text(abs_x + self.width / 2, abs_y + self.height / 2 + self.text_offs_y,
                                  self.text, self.font, fill=self.foreground)
        else:
            raise Exception("Button created with neither image nor text :(")

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int) -> bool:
        if self.enabled:
            if self.x <= x < self.x + self.width and self.y <= y < self.y + self.height:
                if button == 1 and self.on_press:
                    self.on_press(root_x, root_y)
                    return True
        return False


class ButtonBar(Box):
    def __init__(self, x: int, y: int, padding: int = 0, margin: int = 0):
        super().__init__(x, y, padding * 2, padding * 2)
        self.resizeable = False
        self.draggable = False
        self.buttons: list[Button] = []
        self.padding = padding
        self.margin = margin

    def _set_view(self, view: 'View'):
        self.view = view
        for button in self.buttons:
            button.view = view

    def recalc_size(self):
        total_width = self.padding
        max_height = 0
        for button in self.buttons:
            button.x = total_width
            total_width += button.width + self.margin
            button.y = self.padding
            if button.height > max_height:
                max_height = button.height

        total_width -= self.margin  # We added one margin too much
        total_width += self.padding
        self.width = total_width

        self.height = max_height + 2 * self.padding

    def on_paint(self, offs_x: int, offs_y: int):
        abs_x = self.x + offs_x
        abs_y = self.y + offs_y

        # Draw box itself
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.width, abs_y + self.height, fill=self.fill)
        # Draw buttons
        for button in self.buttons:
            button.on_paint(abs_x, abs_y)

    def on_click(self, mouse_button: int, x: int, y: int, root_x: int, root_y: int):
        for button in self.buttons:
            if button.on_click(mouse_button, x, y, root_x, root_y):
                return

    def add_button(self, button: Button):
        self.buttons.append(button)
        self.recalc_size()
