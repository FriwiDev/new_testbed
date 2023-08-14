import threading
import typing

from gui.box import Box
from gui.button import ButtonBar, Button
from gui.images import Images
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
        self.on_off_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, Images.run, "O",
                                    "Arial " + str(int(self.view.gui_scale * 20)),
                                    on_press=lambda x, y: self.on_press_on_off())
        self.ping_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, Images.ping_disabled, "P",
                                  "Arial " + str(int(self.view.gui_scale * 20)),
                                  on_press=lambda x, y: self.on_press_ping_or_iperf(lambda x: self.on_ping_select(x)))
        self.iperf_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, Images.iperf_disabled, "S",
                                   "Arial " + str(int(self.view.gui_scale * 20)),
                                   on_press=lambda x, y: self.on_press_ping_or_iperf(lambda x: self.on_iperf_select(x)))
        self.destroy_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, Images.destroy, "D",
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
                self.fill = self.get_selectable_color()
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
            if self.view.in_toggle:
                self.on_off_button.enabled = False
                self.destroy_button.enabled = False
                self.on_off_button.image = Images.wait
                self.destroy_button.image = Images.wait
            else:
                self.on_off_button.enabled = True
                self.destroy_button.enabled = True
                self.on_off_button.image = Images.stop if self.service.status == EngineComponentStatus.RUNNING else Images.run
                self.destroy_button.image = Images.destroy
            if self.service.status == EngineComponentStatus.RUNNING:
                self.ping_button.enabled = True
                self.iperf_button.enabled = True
                self.ping_button.image = Images.ping_enabled
                self.iperf_button.image = Images.iperf_enabled
            else:
                self.ping_button.enabled = False
                self.iperf_button.enabled = False
                self.ping_button.image = Images.ping_disabled
                self.iperf_button.image = Images.iperf_disabled

            self.button_bar._set_view(self.view)
            self.button_bar.x = offs_x + self.x * self.view.zoom + self.width / 2 * self.view.zoom - self.button_bar.width / 2
            self.button_bar.y = offs_y + self.y * self.view.zoom - self.button_bar.height

    def on_focus_gain(self):
        self.view.set_active_button_bar(self.button_bar)

    def on_focus_loose(self):
        if self.view.active_button_bar == self.button_bar:
            self.view.set_active_button_bar(None)

    def on_press_on_off(self):
        if self.view.in_toggle:
            return
        self.view.in_toggle = True
        thread = threading.Thread(target=self.do_toggle_online)
        thread.start()
        pass

    def do_toggle_online(self):
        if self.service.status == EngineComponentStatus.UNREACHABLE:
            self.view.set_message(f"Can not start {self.service.get_name()}: currently unreachable", color='#FF0000')
        elif self.service.status == EngineComponentStatus.RUNNING:
            self.view.set_message(f"Stopping {self.service.get_name()}...")
            self.service.engine.stop(self.service.component)
            self.view.set_message(f"Stopped {self.service.get_name()}")
        else:
            self.view.set_message(f"Starting {self.service.get_name()}...")
            self.service.engine.start(self.service.component)
            self.view.set_message(f"Started {self.service.get_name()}")
        self.view.in_toggle = False

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
            self.view.set_message("No target reachable from this component", color='#FF0000')
            return
        self.view.set_message("Please select a target", color='#FFFFFF', cd=60*60*1000)
        self.view.set_select_mode(reachable)
        self.view.select_callback = callback

    def on_ping_select(self, box: 'ServiceBox' or 'InterfaceBox' or None):
        self.view.set_select_mode(None)
        self.view.select_callback = None
        self.view.set_message("")
        if not box:
            return
        center_x = self.view.box.x + self.view.gui.main_box.x + self.view.width / self.view.zoom / 2
        center_y = self.view.box.y + self.view.gui.main_box.y + self.view.height / self.view.zoom / 2
        w = 400
        h = 200
        self.stat_boxes.append(StatBoxUtil.create_ping_box(self.view,
                                                           int(center_x - w / 2), int(center_y - h / 2), w, h,
                                                           self.service,
                                                           box.intf if isinstance(box, InterfaceBox) else box.service))

    def on_iperf_select(self, box: 'ServiceBox' or 'InterfaceBox' or None):
        self.view.set_select_mode(None)
        self.view.select_callback = None
        self.view.set_message("")
        if not box:
            return
        if isinstance(box, InterfaceBox):
            target = box.intf.parent.component
            target_dev = box.intf.component
            target_dev_eng = box.intf
        else:
            target = box.service.component
            target_dev = target
            target_dev_eng = box.service
        self.view.set_message(f"Running Iperf {self.service.get_name()} -> {target_dev_eng.get_name()} in background...")
        thread = threading.Thread(target=lambda: self.run_iperf(target, target_dev))
        thread.start()

    def run_iperf(self, target, target_dev):
        self.service.engine.cmd_iperf(self.service.component, target, target_dev)

    def on_press_destroy(self):
        if self.view.in_toggle:
            return
        self.view.in_toggle = True
        thread = threading.Thread(target=self.do_destroy)
        thread.start()
        pass

    def do_destroy(self):
        if self.service.status == EngineComponentStatus.UNREACHABLE:
            self.view.set_message(f"Can not destroy {self.service.get_name()}: currently unreachable", color='#FF0000')
        elif self.service.status == EngineComponentStatus.REMOVED:
            self.view.set_message(f"Can not destroy {self.service.get_name()}: already removed", color='#FF0000')
        else:
            self.view.set_message(f"Destroying {self.service.get_name()}...")
            self.service.engine.destroy(self.service.component)
            self.view.set_message(f"Destroyed {self.service.get_name()}")
        self.view.in_toggle = False

    def _list_boxes(self, parent: Box) -> typing.List[Box]:
        ret = list(parent.subboxes)
        for box in parent.subboxes:
            for sub in self._list_boxes(box):
                ret.append(sub)
        return ret

    def get_selectable_color(self):
        if self.view.select_mode:
            if self in self.view.select_mode and \
                    self.service.status != EngineComponentStatus.RUNNING:
                return '#FFC0C0'
        return '#FFFFFF'
