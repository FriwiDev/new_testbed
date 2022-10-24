import math

from gui.box import Box


class StatBox(Box):
    DEFAULT_UNIT = 0
    SECONDS_UNIT = 1
    BYTES_UNIT = 2
    BITS_UNIT = 3

    def __init__(self, x: int, y: int, width: int, height: int):
        super(StatBox, self).__init__(x, y, width, height)
        self.title = "<Unknown>"
        self.x_axis = "<Unknown>"
        self.y_axis = "<Unknown>"
        self.x_unit = StatBox.DEFAULT_UNIT
        self.y_unit = StatBox.DEFAULT_UNIT
        self.data: dict[float, (float, str)] = {}  # X -> (Y, color)
        self.minimal_y = 0  # None would mean scaling lower y value dynamically

    def on_paint(self, offs_x: int, offs_y: int):
        abs_x = self.x + offs_x
        abs_y = self.y + offs_y
        # Draw box itself
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.width, abs_y + self.height, fill=self.fill)
        # Draw Title
        self.view.create_text(abs_x + self.width / 2, abs_y + 12, self.title, "Arial 10")
        title_height = 24
        text_offs = 10
        axis_offs = 40
        axis_border = 10
        min_x = self.min_x()
        min_y = self.min_y()
        max_x = self.max_x()
        max_y = self.max_y()
        if min_x == max_x:
            max_x += 1
        if min_y == max_y:
            max_y += 1
        # Axis text
        l = len(self.data.keys())
        content_x_offs = 5
        content_spacing = 10
        x_amount = int((self.width - axis_offs - axis_border - content_x_offs - content_spacing) / 15)
        if x_amount > l:
            x_amount = l
        x_step = self.unit_step(min_x, max_x, x_amount)
        x_begin = int(min_x) - int(min_x) % x_step
        if x_begin < min_x:
            x_begin += x_step

        y_amount = int((self.height - title_height - axis_offs - content_spacing) / 15)
        y_step = self.unit_step(min_y, max_y, y_amount)
        y_begin = int(min_y) - int(min_y) % y_step
        if y_begin < min_y:
            y_begin += y_step
        # Draw axis steps
        unit_width = (self.width - axis_offs - axis_border - content_x_offs - content_spacing) / (l + 1)
        unit_height = (self.height - title_height - axis_offs - content_spacing)
        i = 0
        while True:
            perc = (x_begin + i * x_step - min_x) / (max_x - min_x)
            x_perc = abs_x + axis_offs + content_x_offs \
                     + perc * (self.width - axis_offs - axis_border - content_x_offs - content_spacing) / (l + 1) * l \
                     + unit_width / 2
            if x_begin + i * x_step > max_x:
                break
            self.view.canvas.create_line(x_perc,
                                         abs_y + self.height - axis_offs,
                                         x_perc,
                                         abs_y + self.height - axis_offs + 5)
            i += 1
        i = 0
        while True:
            perc = (y_begin + i * y_step - min_y) / (max_y - min_y)
            if y_begin + i * y_step > max_y:
                break
            if 0.001 < perc < 0.999:
                y_perc = abs_y + self.height - axis_offs \
                         - perc * (self.height - axis_offs - title_height)
                self.view.canvas.create_line(abs_x + axis_offs - 5,
                                             y_perc,
                                             abs_x + axis_offs,
                                             y_perc)
            i += 1
        # Draw content
        for x in self.data.keys():
            y, color = self.data[x]
            if y == math.inf or y > max_y:
                perc_y = 1
            elif y <= min_y:
                perc_y = 0
            else:
                perc_y = (y - min_y) / (max_y - min_y)
            perc_x = (x - min_x) / (max_x - min_x)
            calc_x = abs_x + axis_offs + content_x_offs + unit_width * l * perc_x
            self.view.canvas.create_rectangle(calc_x + 1,
                                              abs_y + self.height - axis_offs - (unit_height * perc_y),
                                              calc_x + unit_width - 1,
                                              abs_y + self.height - axis_offs,
                                              fill=color,
                                              outline='')

        # Draw X-Axis
        self.view.create_text(abs_x + self.width / 2, abs_y + self.height - text_offs, self.x_axis, "Arial 8")
        self.view.canvas.create_line(abs_x + axis_offs, abs_y + self.height - axis_offs,
                                     abs_x + self.width - axis_border, abs_y + self.height - axis_offs,
                                     arrow="last", arrowshape=(6, 10, 4))

        # Draw Y-Axis
        self.view.create_text(abs_x + text_offs, abs_y + self.height / 2, self.y_axis, "Arial 8", angle=270)
        self.view.canvas.create_line(abs_x + axis_offs, abs_y + self.height - axis_offs,
                                     abs_x + axis_offs, abs_y + title_height,
                                     arrow="last", arrowshape=(6, 10, 4))

    def calculate_min_width(self):
        return 200

    def calculate_min_height(self):
        return 100

    def add_value(self, x: float, y: float, color: str = '#C0C0FF'):
        self.data[x] = (y, color)

    def prune_history(self, min_x: float):
        for i in list(self.data.keys()):
            if i < min_x:
                del self.data[i]

    def min_x(self) -> float:
        min_x = math.inf
        for x in self.data.keys():
            if min_x > x:
                min_x = x
        if min_x == math.inf:
            return 0
        return min_x

    def max_x(self) -> float:
        max_x = -math.inf
        for x in self.data.keys():
            if max_x < x:
                max_x = x
        if max_x == -math.inf:
            return 1
        return max_x

    def min_y(self) -> float:
        if self.minimal_y:
            return self.minimal_y
        min_y = math.inf
        for y, _ in self.data.values():
            if min_y > y:
                min_y = y
        if min_y == math.inf:
            return 0
        return min_y

    def max_y(self) -> float:
        max_y = -math.inf
        for y, _ in self.data.values():
            if max_y < y != math.inf:
                max_y = y
        if max_y == -math.inf:
            return 1
        return max_y

    def unit_step(self, min: float, max: float, amount: float) -> int:
        diff = max - min
        exp = int(math.log(diff / amount, 10))
        return 10 ** exp
