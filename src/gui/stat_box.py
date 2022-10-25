import math
import time
from threading import Lock

from gui.box import Box
from live.engine import Engine
from live.engine_component import EngineComponent


class StatBox(Box):
    DEFAULT_UNIT = 0
    MILLISECONDS_UNIT = 1
    BITS_PER_SEC_UNIT = 2

    DEFAULT_UNIT_SUFFIXES = ["", "K", "M", "G", "T"]
    MILLISECONDS_UNIT_SUFFIXES = ["ms", "s"]
    BITS_PER_SEC_UNIT_SUFFIXES = ["Bit/s", "KBit/s", "MBit/s", "GBit/s", "TBit/s"]

    def __init__(self, x: int, y: int, width: int, height: int):
        super(StatBox, self).__init__(x, y, width, height)
        self.title = "<Unknown>"
        self.x_axis = "<Unknown>"
        self.y_axis = "<Unknown>"
        self.x_unit = StatBox.DEFAULT_UNIT
        self.y_unit = StatBox.DEFAULT_UNIT
        self.data: dict[float, (float, str)] = {}  # X -> (Y, color)
        self.minimal_y = 0  # None would mean scaling lower y value dynamically
        self.data_lock = Lock()

    def on_paint(self, offs_x: int, offs_y: int):
        self.data_lock.acquire()
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
        x_amount = int((self.width - axis_offs - axis_border - content_x_offs - content_spacing) / 80)
        if x_amount > l:
            x_amount = l
        if x_amount <= 0:
            x_amount = 1
        x_step = self.unit_step(min_x, max_x, x_amount)
        x_begin = int(min_x) - int(min_x) % x_step
        if x_begin < min_x:
            x_begin += x_step

        y_amount = int((self.height - title_height - axis_offs - content_spacing) / 80)
        if y_amount <= 0:
            y_amount = 1
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
            if i % 5 == 0:
                self.view.create_text(x_perc, abs_y + self.height - axis_offs + 10,
                                      self.format_unit(x_step, self.x_unit, x_begin + i * x_step), "Arial 6")
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
                if i == 1 or i % 5 == 0:
                    self.view.create_text(abs_x + axis_offs - 10, y_perc,
                                          self.format_unit(y_step, self.y_unit, y_begin + i * y_step),
                                          "Arial 6", angle=270)
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
        self.view.create_text(abs_x + self.width / 2, abs_y + self.height - text_offs,
                              self.x_axis + self.format_unit_suffix(x_step, self.x_unit), "Arial 8")
        self.view.canvas.create_line(abs_x + axis_offs, abs_y + self.height - axis_offs,
                                     abs_x + self.width - axis_border, abs_y + self.height - axis_offs,
                                     arrow="last", arrowshape=(6, 10, 4))

        # Draw Y-Axis
        self.view.create_text(abs_x + text_offs, abs_y + self.height / 2,
                              self.y_axis + self.format_unit_suffix(y_step, self.y_unit), "Arial 8", angle=270)
        self.view.canvas.create_line(abs_x + axis_offs, abs_y + self.height - axis_offs,
                                     abs_x + axis_offs, abs_y + title_height,
                                     arrow="last", arrowshape=(6, 10, 4))

        self.data_lock.release()

    def calculate_min_width(self):
        return 200

    def calculate_min_height(self):
        return 100

    def add_value(self, x: float, y: float, color: str = '#C0C0FF'):
        self.data_lock.acquire()
        self.data[x] = (y, color)
        self.data_lock.release()

    def prune_history(self, min_x: float):
        self.data_lock.acquire()
        for i in list(self.data.keys()):
            if i < min_x:
                del self.data[i]
        self.data_lock.release()

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
        exp = math.floor(math.log(diff / amount, 10))
        return 10 ** exp

    def format_unit(self, unit_step: int, unit: int, value: float) -> str:
        suffix = 0
        max_suffix = len(self.get_suffixes_for_unit(unit)) - 1
        while unit_step >= 1000:
            unit_step /= 1000
            value /= 1000
            if suffix < max_suffix:
                suffix += 1
        if suffix >= len(StatBox.DEFAULT_UNIT_SUFFIXES):
            suffix = len(StatBox.DEFAULT_UNIT_SUFFIXES) - 1
        return format(value, ".1f").replace(".0", "")\
               + (StatBox.DEFAULT_UNIT_SUFFIXES[suffix] if unit == StatBox.DEFAULT_UNIT else "")

    def format_unit_suffix(self, unit_step: int, unit: int) -> str:
        if unit == StatBox.DEFAULT_UNIT:
            return ""
        elif unit == StatBox.MILLISECONDS_UNIT:
            if unit_step >= 1000:
                return " (s)"
            else:
                return " (ms)"
        elif unit == StatBox.BITS_PER_SEC_UNIT:
            suffix = 0
            while unit_step >= 1000:
                unit_step /= 1000
                suffix += 1
            if suffix >= len(StatBox.BITS_PER_SEC_UNIT_SUFFIXES):
                suffix = len(StatBox.BITS_PER_SEC_UNIT_SUFFIXES) - 1
            return " (" + StatBox.BITS_PER_SEC_UNIT_SUFFIXES[suffix] + ")"

    def get_suffixes_for_unit(self, unit: int):
        if unit == StatBox.DEFAULT_UNIT:
            return StatBox.DEFAULT_UNIT_SUFFIXES
        elif unit == StatBox.MILLISECONDS_UNIT:
            return StatBox.MILLISECONDS_UNIT_SUFFIXES
        elif unit == StatBox.BITS_PER_SEC_UNIT:
            return StatBox.BITS_PER_SEC_UNIT_SUFFIXES
        else:
            raise Exception("Invalid unit")



class StatBoxDataSupplier(object):
    PING = 0
    IFSTAT_RX = 1
    IFSTAT_TX = 2

    def __init__(self, engine: Engine, box: StatBox, type: int, source: EngineComponent, target: EngineComponent = None,
                 history: float = -1):
        self.engine = engine
        self.box = box
        self.type = type
        self.source = source
        self.target = target
        self.history = history
        self.stop_updating = False
        if type == 0:
            if self.history == -1:
                self.history = 20
            box.title = f"Ping {source.get_name()} -> {target.get_name()}"
            box.y_axis = f"Time"
            box.x_axis = f"ICMP seq"
            box.y_unit = StatBox.MILLISECONDS_UNIT
            box.x_unit = StatBox.DEFAULT_UNIT
            box.minimal_y = 0
        elif type == 1:
            if self.history == -1:
                self.history = 20000
            box.title = f"RX {source.get_name()}"
            box.y_axis = f"Receiving rate"
            box.x_axis = f"Time"
            box.y_unit = StatBox.BITS_PER_SEC_UNIT
            box.x_unit = StatBox.MILLISECONDS_UNIT
            box.minimal_y = 0
        elif type == 2:
            if self.history == -1:
                self.history = 20000
            box.title = f"TX {source.get_name()}"
            box.y_axis = f"Transmission rate"
            box.x_axis = f"Time"
            box.y_unit = StatBox.BITS_PER_SEC_UNIT
            box.x_unit = StatBox.MILLISECONDS_UNIT
            box.minimal_y = 0
        else:
            raise Exception("Invalid type")

    def run_chart(self):
        if self.type == 0:
            for i in range(0, int(self.history)):
                self.box.add_value(-i, 0)
            icmp_offs = 0
            while not self.engine.stop_updating and not self.stop_updating:
                icmp_offs += 1
                values = self.engine.cmd_ping(self.source.component, self.target.component, 1).ping_results.values()
                if len(values) >= 1:
                    for res in values:
                        if isinstance(res, str):
                            # Ping failed
                            self.box.add_value(icmp_offs, math.inf, '#FFC0C0')
                        else:
                            ttl, ti = res
                            self.box.add_value(icmp_offs, int(ti * 1000))
                        break
                else:
                    # Ping failed
                    self.box.add_value(icmp_offs, math.inf, '#FFC0C0')
                self.box.prune_history(icmp_offs - self.history)
                time.sleep(0.7)
        elif self.type == 1 or self.type == 2:
            for i in range(0, int(self.history / 1000)):
                self.box.add_value(-i * 1000, 0)
            start = 0
            while not self.engine.stop_updating and not self.stop_updating:
                start += 1000
                if self.source.ifstat:
                    rx, tx = self.source.ifstat
                    color = '#C0C0C0'
                else:
                    rx = math.inf
                    tx = math.inf
                    color = '#C0C0FF'
                self.box.add_value(start, rx if type == 1 else tx, color)
                self.box.prune_history(start - self.history)
                time.sleep(1)
        else:
            raise Exception("Invalid type")
