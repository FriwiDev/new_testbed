import math
import threading
import time
from threading import Lock

from gui.box import Box
from gui.images import Images
from live.engine import Engine
from live.engine_component import EngineComponent, EngineInterface, EngineService, EngineComponentStatus


class StatBox(Box):
    DEFAULT_UNIT = 0
    MILLISECONDS_UNIT = 1
    BITS_PER_SEC_UNIT = 2

    DEFAULT_UNIT_SUFFIXES = ["", "K", "M", "G", "T"]
    MILLISECONDS_UNIT_SUFFIXES = ["us", "ms", "s"]
    BITS_PER_SEC_UNIT_SUFFIXES = ["Bit/s", "KBit/s", "MBit/s", "GBit/s", "TBit/s"]

    def __init__(self, x: int, y: int, width: int, height: int, view: 'View'):
        self.view = view
        super(StatBox, self).__init__(x, y, width, height)
        self.title = "<Unknown>"
        self.x_axis = "<Unknown>"
        self.y_axis = "<Unknown>"
        self.x_unit = StatBox.DEFAULT_UNIT
        self.y_unit = StatBox.DEFAULT_UNIT
        self.data: dict[float, (float, str)] = {}  # X -> (Y, color)
        self.minimal_y = 0  # None would mean scaling lower y value dynamically
        self.data_lock = Lock()
        self.data_supplier = None
        self.cross = None
        self.cross_size = None
        self.fill = 'white'

    def on_paint(self, offs_x: int, offs_y: int):
        self.data_lock.acquire()
        abs_x = self.x * self.view.zoom + offs_x
        abs_y = self.y * self.view.zoom + offs_y
        # Draw box itself
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.width * self.view.zoom,
                                          abs_y + self.height * self.view.zoom,
                                          fill=self.fill, width=self.view.zoom)
        # Draw Title
        self.view.create_text(abs_x + self.width / 2 * self.view.zoom, abs_y + 12 * self.view.zoom, self.title,
                              "Arial " + str(int(10 * self.view.zoom)))
        title_height = 24
        text_offs = 14
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
            x_perc = abs_x + (axis_offs + content_x_offs \
                              + perc * (self.width - axis_offs - axis_border - content_x_offs - content_spacing) / (
                                      l + 1) * l \
                              + unit_width / 2) * self.view.zoom
            if x_begin + i * x_step > max_x:
                break
            self.view.canvas.create_line(x_perc,
                                         abs_y + (self.height - axis_offs) * self.view.zoom,
                                         x_perc,
                                         abs_y + (self.height - axis_offs + 5) * self.view.zoom,
                                         width=self.view.zoom)
            if i % 5 == 0:
                self.view.create_text(x_perc, abs_y + (self.height - axis_offs + 12) * self.view.zoom,
                                      self.format_unit(x_step, self.x_unit, x_begin + i * x_step),
                                      "Arial " + str(int(6 * self.view.zoom)))
            i += 1
        i = 0
        while True:
            perc = (y_begin + i * y_step - min_y) / (max_y - min_y)
            if y_begin + i * y_step > max_y:
                break
            if 0.001 < perc < 0.999:
                y_perc = abs_y + (self.height - axis_offs \
                                  - perc * (self.height - axis_offs - title_height)) * self.view.zoom
                self.view.canvas.create_line(abs_x + (axis_offs - 5) * self.view.zoom,
                                             y_perc,
                                             abs_x + axis_offs * self.view.zoom,
                                             y_perc,
                                             width=self.view.zoom)
                if i == 1 or i % 5 == 0:
                    self.view.create_text(abs_x + (axis_offs - 12) * self.view.zoom, y_perc,
                                          self.format_unit(y_step, self.y_unit, y_begin + i * y_step),
                                          "Arial " + str(int(6 * self.view.zoom)), angle=270)
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
            calc_x = abs_x + (axis_offs + content_x_offs + unit_width * l * perc_x) * self.view.zoom
            self.view.canvas.create_rectangle(calc_x + 1 * self.view.zoom,
                                              abs_y + (self.height - axis_offs - (
                                                      unit_height * perc_y)) * self.view.zoom,
                                              calc_x + (unit_width - 1) * self.view.zoom,
                                              abs_y + (self.height - axis_offs) * self.view.zoom,
                                              fill=color,
                                              outline='')

        # Draw X-Axis
        self.view.create_text(abs_x + self.width / 2 * self.view.zoom,
                              abs_y + (self.height - text_offs) * self.view.zoom,
                              self.x_axis + self.format_unit_suffix(x_step, self.x_unit),
                              "Arial " + str(int(8 * self.view.zoom)))
        self.view.canvas.create_line(abs_x + axis_offs * self.view.zoom,
                                     abs_y + (self.height - axis_offs) * self.view.zoom,
                                     abs_x + (self.width - axis_border) * self.view.zoom,
                                     abs_y + (self.height - axis_offs) * self.view.zoom,
                                     arrow="last",
                                     arrowshape=(6 * self.view.zoom, 10 * self.view.zoom, 4 * self.view.zoom),
                                     width=self.view.zoom)

        # Draw Y-Axis
        self.view.create_text(abs_x + text_offs * self.view.zoom, abs_y + (self.height / 2) * self.view.zoom,
                              self.y_axis + self.format_unit_suffix(y_step, self.y_unit),
                              "Arial " + str(int(8 * self.view.zoom)), angle=270)
        self.view.canvas.create_line(abs_x + axis_offs * self.view.zoom,
                                     abs_y + (self.height - axis_offs) * self.view.zoom,
                                     abs_x + axis_offs * self.view.zoom, abs_y + title_height * self.view.zoom,
                                     arrow="last",
                                     arrowshape=(6 * self.view.zoom, 10 * self.view.zoom, 4 * self.view.zoom),
                                     width=self.view.zoom)

        # Draw cross
        cross_width = 20
        cross_offs = 5

        cross_size = int(cross_width * self.view.zoom)
        if not self.cross or not self.cross_size or self.cross_size != cross_size:
            self.cross_size = cross_size
            self.cross = Images.get_with_size(Images.close, self.cross_size, self.cross_size)
        self.view.canvas.create_image(offs_x + (self.x + self.width - cross_offs - cross_width / 2) * self.view.zoom,
                                      offs_y + (self.y + cross_offs + cross_width / 2) * self.view.zoom,
                                      image=self.cross)

        self.data_lock.release()

    def calculate_min_width(self):
        return 400

    def calculate_min_height(self):
        return 200

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
        if self.minimal_y is not None:
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
        return format(value, ".1f").replace(".0", "") \
               + (StatBox.DEFAULT_UNIT_SUFFIXES[suffix] if unit == StatBox.DEFAULT_UNIT else "")

    def format_unit_suffix(self, unit_step: int, unit: int) -> str:
        if unit == StatBox.DEFAULT_UNIT:
            return ""
        elif unit == StatBox.MILLISECONDS_UNIT:
            if unit_step >= 1000000:
                return " (s)"
            elif unit_step >= 1000:
                return " (ms)"
            else:
                return " (us)"
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

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        cross_width = 20
        cross_offs = 5
        if not self.view.select_mode:
            if self.width - cross_width - cross_offs <= x < self.width - cross_offs \
                    and cross_offs <= y < cross_width + cross_offs:
                self.parent.subboxes.remove(self)
                if self.data_supplier:
                    self.data_supplier.stop_updating = True
                return
        super(StatBox, self).on_click(button, x, y, root_x, root_y)

    def update_fill(self):
        self.fill = 'white'


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
        box.data_supplier = self
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
                if self.source.ifstat and self.source.status == EngineComponentStatus.RUNNING:
                    rx, tx = self.source.ifstat
                    color = '#C0C0FF'
                else:
                    rx = math.inf
                    tx = math.inf
                    color = '#FFC0C0'
                self.box.add_value(start, rx if self.type == 1 else tx, color)
                self.box.prune_history(start - self.history)
                time.sleep(1)
        else:
            raise Exception("Invalid type")


class StatBoxUtil(object):
    @classmethod
    def create_traffic_box(cls, view: 'MainView', type: int, x: int, y: int, w: int, h: int,
                           intf: EngineInterface) -> StatBox:
        stat = StatBox(x, y, w, h, view)
        stat.available_bounding_boxes = [(0, 0, view.box.width, view.box.height, 0)]
        stat.current_box = (0, 0, view.box.width, view.box.height, 0)
        supp = StatBoxDataSupplier(intf.engine, stat, type, intf)
        stat.data_supplier = supp
        update_thread = threading.Thread(target=supp.run_chart)
        update_thread.start()
        view.gui.main_box.add_box(stat)
        return stat

    @classmethod
    def create_ping_box(cls, view: 'MainView', x: int, y: int, w: int, h: int,
                        service1: EngineService, service2: EngineService or EngineInterface) -> StatBox:
        stat = StatBox(x, y, w, h, view)
        stat.available_bounding_boxes = [(0, 0, view.box.width, view.box.height, 0)]
        stat.current_box = (0, 0, view.box.width, view.box.height, 0)
        supp = StatBoxDataSupplier(service1.engine, stat, StatBoxDataSupplier.PING, service1, service2)
        stat.data_supplier = supp
        update_thread = threading.Thread(target=supp.run_chart)
        update_thread.start()
        view.gui.main_box.add_box(stat)
        return stat

    @classmethod
    def create_stat_box(cls, data: list, view: 'MainView', engine: 'Engine') -> StatBox or None:
        # type, x, y, width, height, source, [target]
        type = int(data[0])
        stat = StatBox(int(data[1]), int(data[2]), int(data[3]), int(int(data[4])), view)
        stat.available_bounding_boxes = [(0, 0, view.box.width, view.box.height, 0)]
        stat.current_box = (0, 0, view.box.width, view.box.height, 0)
        if type == StatBoxDataSupplier.IFSTAT_RX or type == StatBoxDataSupplier.IFSTAT_TX:
            intf1 = cls._get_intf_if_exists(engine, data[5])
            if not intf1:
                return None
            supp = StatBoxDataSupplier(engine, stat, type, intf1)
        elif type == StatBoxDataSupplier.PING:
            service1 = cls._get_service_if_exists(engine, data[5])
            target2 = cls._get_service_or_intf_if_exists(engine, data[6])
            if not service1 or not target2:
                return None
            supp = StatBoxDataSupplier(engine, stat, type, service1, target2)
        else:
            raise Exception("Invalid stat type")
        stat.data_supplier = supp
        update_thread = threading.Thread(target=supp.run_chart)
        update_thread.start()
        view.gui.main_box.add_box(stat)
        return stat

    @classmethod
    def get_data(cls, stat: StatBox):
        type = stat.data_supplier.type
        ret = [type, stat.x, stat.y, stat.width, stat.height]
        if type == StatBoxDataSupplier.IFSTAT_RX or type == StatBoxDataSupplier.IFSTAT_TX:
            source = stat.data_supplier.source
            sx = source.parent.component.name + "; " + source.component.name
            if isinstance(source.parent, EngineService):
                sx = source.parent.parent.component.name + "; " + sx
            ret.append(sx)
        elif type == StatBoxDataSupplier.PING:
            source = stat.data_supplier.source
            sx = source.parent.component.name + "; " + source.component.name
            target = stat.data_supplier.target
            tx = target.parent.component.name + "; " + target.component.name
            if isinstance(target, EngineInterface):
                tx = target.parent.parent.component.name + "; " + tx
            ret.append(sx)
            ret.append(tx)
        else:
            raise Exception("Invalid stat type")
        return ret

    @classmethod
    def _get_intf_if_exists(cls, engine: 'Engine', name: str) -> EngineInterface or None:
        split = name.split("; ")
        if split[0] in engine.nodes.keys():
            node = engine.nodes[split[0]]
            if len(split) == 2:
                if split[1] in node.intfs.keys():
                    return node.intfs[split[1]]
            else:
                if split[1] in node.services.keys():
                    service = node.services[split[1]]
                    if split[2] in service.intfs.keys():
                        return service.intfs[split[2]]
        return None

    @classmethod
    def _get_service_or_intf_if_exists(cls, engine: 'Engine', name: str) -> EngineInterface or None:
        split = name.split("; ")
        if split[0] in engine.nodes.keys():
            node = engine.nodes[split[0]]
            if len(split) == 2:
                if split[1] in node.services.keys():
                    return node.services[split[1]]
            else:
                if split[1] in node.services.keys():
                    service = node.services[split[1]]
                    if split[2] in service.intfs.keys():
                        return service.intfs[split[2]]
        return None

    @classmethod
    def _get_service_if_exists(cls, engine: 'Engine', name: str) -> EngineService or None:
        split = name.split("; ")
        if split[0] in engine.nodes.keys():
            node = engine.nodes[split[0]]
            if split[1] in node.services.keys():
                return node.services[split[1]]
        return None
