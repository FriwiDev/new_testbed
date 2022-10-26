import threading

from gui.box import Box
from gui.button import ButtonBar, Button
from gui.interface_box import InterfaceBox
from gui.stat_box import StatBoxUtil
from gui.system_box import SystemBox
from live.engine_component import EngineService, EngineComponentStatus


class ServiceBox(SystemBox):
    def __init__(self, service: EngineService, view: 'View'):
        super().__init__(service.component.gui_data.x, service.component.gui_data.y,
                         service.component.gui_data.width, service.component.gui_data.height)
        self.service = service
        self.view = view

        self.button_bar = ButtonBar(self.x, self.y, 3, 3)
        self.on_off_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "O", "Arial " + str(int(self.view.gui_scale * 20)),
                                    on_press=lambda x, y: self.on_press_on_off())
        self.ping_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "P",
                                  "Arial " + str(int(self.view.gui_scale * 20)),
                                  on_press=lambda x, y: self.on_press_ping_or_iperf(lambda x: self.on_ping_select(x)))
        self.iperf_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "S",
                                   "Arial " + str(int(self.view.gui_scale * 20)),
                                   on_press=lambda x, y: self.on_press_ping_or_iperf(lambda x: self.on_iperf_select(x)))
        self.destroy_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "D",
                                     "Arial " + str(int(self.view.gui_scale * 20)),
                                     on_press=lambda x, y: self.on_press_destroy())
        self.button_bar.add_button(self.on_off_button)
        self.button_bar.add_button(self.ping_button)
        self.button_bar.add_button(self.iperf_button)
        self.button_bar.add_button(self.destroy_button)
        self.stat_boxes = []
        for data in self.service.component.gui_data.stat_data:
            b = StatBoxUtil.create_stat_box(data, self.view, service.engine)
            if b:
                self.stat_boxes.append(b)

    def rebuild_gui_data(self):
        for box in list(self.stat_boxes):
            if box.data_supplier.stop_updating:
                # Stat box got closed
                self.stat_boxes.remove(box)
        self.service.component.gui_data.stat_data = [StatBoxUtil.get_data(x) for x in self.stat_boxes]

    def on_resize(self, width: int, height: int):
        super(ServiceBox, self).on_resize(width, height)
        self.service.component.gui_data.x = self.x
        self.service.component.gui_data.y = self.y
        self.service.component.gui_data.width = self.width
        self.service.component.gui_data.height = self.height

    def on_paint(self, offs_x: int, offs_y: int):
        if self.view.select_mode:
            if self in self.view.select_mode:
                self.fill = '#FFFFFF'
            else:
                self.fill = '#7C7C7C'
        elif self.service.status == EngineComponentStatus.RUNNING:
            self.fill = 'white'
        else:
            self.fill = '#707070'
        super().on_paint(offs_x, offs_y)
        abs_x = self.x * self.view.zoom + offs_x
        abs_y = self.y * self.view.zoom + offs_y
        self.view.create_text(abs_x + self.width / 2 * self.view.zoom,
                              abs_y + self.height / 2 * self.view.zoom - 2 * self.view.gui_scale,
                              self.service.component.name,
                              font="Arial " + str(int(12 * self.view.zoom)))

        if self.focus:
            self.button_bar._set_view(self.view)
            self.button_bar.x = offs_x+self.x*self.view.zoom+self.width/2*self.view.zoom-self.button_bar.width/2
            self.button_bar.y = offs_y+self.y*self.view.zoom-self.button_bar.height

    def on_focus_gain(self):
        self.view.set_active_button_bar(self.button_bar)

    def on_focus_loose(self):
        if self.view.active_button_bar == self.button_bar:
            self.view.set_active_button_bar(None)

    def on_press_on_off(self):
        pass

    def on_press_ping_or_iperf(self, callback):
        reachable = []
        for box in self._list_boxes(self.view.box):
            if isinstance(box, ServiceBox):
                # Check if we can reach service
                if self.service.engine.calculate_ip(self.service.component, box.service.component):
                    reachable.append(box)
            elif isinstance(box, InterfaceBox):
                # Check if we can reach interface
                if self.service.engine.calculate_ip(self.service.component, box.intf.component):
                    reachable.append(box)
        if len(reachable) == 0:
            # TODO Report error in lower font
            return
        self.view.set_select_mode(reachable)
        self.view.select_callback = callback

    def on_ping_select(self, box: 'ServiceBox' or 'InterfaceBox' or None):
        self.view.set_select_mode(None)
        self.view.select_callback = None
        if not box:
            return
        center_x = 1920 / 2  # TODO Adapt
        center_y = 1080 / 2
        w = 400
        h = 200
        self.stat_boxes.append(StatBoxUtil.create_ping_box(self.view,
                                                           int(center_x - w / 2), int(center_y - h / 2), w, h,
                                                           self.service,
                                                           box.intf if isinstance(box, InterfaceBox) else box.service))

    def on_iperf_select(self, box: 'ServiceBox' or 'InterfaceBox' or None):
        self.view.set_select_mode(None)
        self.view.select_callback = None
        if not box:
            return
        if isinstance(box, InterfaceBox):
            target = box.intf.parent.component
            target_dev = box.intf.component
        else:
            target = box.service.component
            target_dev = target
        thread = threading.Thread(target=lambda: self.run_iperf(target, target_dev))
        thread.start()

    def run_iperf(self, target, target_dev):
        self.service.engine.cmd_iperf(self.service.component, target, target_dev)

    def on_press_destroy(self):
        pass

    def _list_boxes(self, parent: Box) -> list[Box]:
        ret = list(parent.subboxes)
        for box in parent.subboxes:
            for sub in self._list_boxes(box):
                ret.append(sub)
        return ret
