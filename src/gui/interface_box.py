import threading

from extensions.macvlan_extension import MacVlanServiceExtension
from gui.box import Box
from gui.button import ButtonBar, Button
from gui.stat_box import StatBoxUtil, StatBoxDataSupplier
from live.engine_component import EngineInterface, EngineComponentStatus, EngineInterfaceState
from network.network_utils import NetworkUtils
from ssh.ip_addr_ssh_command import InterfaceState


class InterfaceBox(Box):
    INTERFACE_DEBUG_WIDTH = 220
    INTERFACE_DEBUG_HEIGHT = 130

    def __init__(self, intf: EngineInterface, view: 'View'):
        self.view = view
        super().__init__(intf.component.gui_data.x, intf.component.gui_data.y,
                         intf.component.gui_data.width, intf.component.gui_data.height)
        self.intf = intf
        self.resizeable = False
        self.admin_net = isinstance(intf.extension, MacVlanServiceExtension)

        self.button_bar = ButtonBar(self.x, self.y, 3, 3)
        self.on_off_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "W",
                                    "Arial " + str(int(self.view.gui_scale * 20)),
                                    on_press=lambda x, y: self.on_press_on_off())
        self.debug_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "i",
                                   "Arial " + str(int(self.view.gui_scale * 20)),
                                   on_press=lambda x, y: self.on_press_debug())
        self.rx_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "RX",
                                "Arial " + str(int(self.view.gui_scale * 20)),
                                on_press=lambda x, y: self.on_press_rx_button())
        self.tx_button = Button(40 * self.view.gui_scale, 40 * self.view.gui_scale, None, "TX",
                                "Arial " + str(int(self.view.gui_scale * 20)),
                                on_press=lambda x, y: self.on_press_tx_button())
        self.button_bar.add_button(self.on_off_button)
        self.button_bar.add_button(self.debug_button)
        self.button_bar.add_button(self.rx_button)
        self.button_bar.add_button(self.tx_button)
        self.stat_boxes = []
        for data in self.intf.component.gui_data.stat_data:
            b = StatBoxUtil.create_stat_box(data, self.view, intf.engine)
            if b:
                self.stat_boxes.append(b)
        self.debug = self.intf.component.gui_data.debug

    def rebuild_gui_data(self):
        for box in list(self.stat_boxes):
            if box.data_supplier.stop_updating:
                # Stat box got closed
                self.stat_boxes.remove(box)
        self.intf.component.gui_data.stat_data = [StatBoxUtil.get_data(x) for x in self.stat_boxes]
        self.intf.component.gui_data.debug = self.debug

    def on_resize(self, width: int, height: int):
        super(InterfaceBox, self).on_resize(width, height)
        self.intf.component.gui_data.x = self.x
        self.intf.component.gui_data.y = self.y
        self.intf.component.gui_data.width = self.width
        self.intf.component.gui_data.height = self.height

    def on_paint(self, offs_x: int, offs_y: int):
        if self.view.select_mode:
            if self in self.view.select_mode:
                self.fill = self.get_selectable_color()
            else:
                self.fill = '#7C7C7C'
        elif self.intf.status == EngineComponentStatus.RUNNING:
            if self.admin_net:
                self.fill = "#50FF50"
            else:
                self.fill = 'white'
        else:
            self.fill = '#707070'
        super().on_paint(offs_x, offs_y)
        abs_x = self.x * self.view.zoom + offs_x
        abs_y = self.y * self.view.zoom + offs_y
        angle = 0
        rot = self.get_rotation()
        if rot in [1, 3]:
            angle = 90

        self.view.create_text(abs_x + self.width / 2 * self.view.zoom, abs_y + self.height / 2 * self.view.zoom,
                              self.intf.component.name,
                              font="Arial " + str(int(10 * self.view.zoom)), angle=angle)
        if self.debug:
            if rot == 0:
                self.draw_interface_debug(abs_x + (self.width / 2 - self.INTERFACE_DEBUG_WIDTH / 2) * self.view.zoom,
                                          abs_y - self.INTERFACE_DEBUG_HEIGHT * self.view.zoom)
            elif rot == 3:
                self.draw_interface_debug(abs_x + self.width * self.view.zoom, abs_y + (self.height / 2 - self.INTERFACE_DEBUG_HEIGHT / 2) * self.view.zoom)
            elif rot in [2, -1]:
                self.draw_interface_debug(abs_x + (self.width / 2 - self.INTERFACE_DEBUG_WIDTH / 2) * self.view.zoom,
                                          abs_y + self.height * self.view.zoom)
            elif rot == 1:
                self.draw_interface_debug(abs_x - self.INTERFACE_DEBUG_WIDTH * self.view.zoom,
                                          abs_y + (self.height / 2 - self.INTERFACE_DEBUG_HEIGHT / 2) * self.view.zoom)

        if self.focus:
            if self.view.in_toggle:
                self.on_off_button.text = "W"
                self.on_off_button.enabled = False
            elif self.intf.status == EngineComponentStatus.RUNNING:
                self.on_off_button.text = "Off"
                self.on_off_button.enabled = True
            else:
                self.on_off_button.text = "On"
                self.on_off_button.enabled = True

            self.button_bar._set_view(self.view)
            self.button_bar.x = offs_x + self.x * self.view.zoom + self.width / 2 * self.view.zoom - self.button_bar.width / 2
            self.button_bar.y = offs_y + self.y * self.view.zoom - self.button_bar.height

    def draw_interface_debug(self, abs_x: int, abs_y: int):
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.INTERFACE_DEBUG_WIDTH * self.view.zoom,
                                          abs_y + self.INTERFACE_DEBUG_HEIGHT * self.view.zoom,
                                          fill='#505050', width=self.view.zoom)
        text_color = '#FFFFFF'
        line = 1
        self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2 * self.view.zoom, abs_y + line * 14 * self.view.zoom,
                              f"{self.intf.component.name} <{self.intf.interface_state.name}>", font="Arial "+str(int(8*self.view.zoom)),
                              fill=text_color)
        line += 1
        if self.intf.live_mac:
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2 * self.view.zoom, abs_y + line * 14 * self.view.zoom,
                                  f"{self.intf.live_mac}", font="Arial "+str(int(8*self.view.zoom)),
                                  fill=text_color)
            line += 1
        for ip, net in self.intf.live_ips:
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2 * self.view.zoom, abs_y + line * 14 * self.view.zoom,
                                  f"{ip}/{net.prefixlen}", font="Arial "+str(int(8*self.view.zoom)),
                                  fill=text_color)
            line += 1
        if self.intf.tcqdisc[0] > 0:
            qdisc = f" Delay<{self.format_micro_seconds(self.intf.tcqdisc[0])}, " \
                    f"{self.format_micro_seconds(self.intf.tcqdisc[1])}, " \
                    f"{self.format_percent(self.intf.tcqdisc[2])}>"
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2 * self.view.zoom, abs_y + line * 14 * self.view.zoom,
                                  qdisc, font="Arial "+str(int(8*self.view.zoom)),
                                  fill=text_color)
            line += 1
        if self.intf.tcqdisc[3] > 0:
            qdisc = f" Loss<{self.format_percent(self.intf.tcqdisc[3])}, " \
                    f"{self.format_percent(self.intf.tcqdisc[4])}>"
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2 * self.view.zoom, abs_y + line * 14 * self.view.zoom,
                                  qdisc, font="Arial "+str(int(8*self.view.zoom)),
                                  fill=text_color)
            line += 1
        line += 1
        if self.intf.interface_state != InterfaceState.DOWN:
            if self.intf.ifstat:
                rx_data, tx_data = self.intf.ifstat
                self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2 * self.view.zoom, abs_y + line * 14 * self.view.zoom,
                                      f"RX: {NetworkUtils.format_thousands(rx_data)}B - "
                                      f"TX: {NetworkUtils.format_thousands(tx_data)}B", font="Arial "+str(int(8*self.view.zoom)),
                                      fill=text_color)
                line += 1

    def format_micro_seconds(self, us: int) -> str:
        if us > 1000:
            us /= 1000
            if us > 1000:
                usf = float(us) / 1000
                return format(usf, ".1f").removesuffix(".0") + "s"
            else:
                return str(us) + "ms"
        else:
            return str(us) + "us"

    def format_percent(self, per: float) -> str:
        return format(per * 100, ".1f").removesuffix(".0") + "%"
    
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
        if self.intf.interface_state == EngineInterfaceState.UP:
            self.intf.engine.cmd_set_iface_state(self.intf, EngineInterfaceState.DOWN)
        else:
            self.intf.engine.cmd_set_iface_state(self.intf, EngineInterfaceState.UP)
        self.view.set_message(f"Interface {self.intf.get_name()} set {self.intf.interface_state.name}")
        self.view.in_toggle = False

    def on_press_debug(self):
        self.debug = not self.debug

    def on_press_rx_button(self):
        center_x = 1920 / 2  # TODO Adapt
        center_y = 1080 / 2
        w = 400
        h = 200
        self.stat_boxes.append(StatBoxUtil.create_traffic_box(self.view, StatBoxDataSupplier.IFSTAT_RX,
                                                              int(center_x - w / 2), int(center_y - h / 2), w, h,
                                                              self.intf))

    def on_press_tx_button(self):
        center_x = 1920 / 2  # TODO Adapt
        center_y = 1080 / 2
        w = 400
        h = 200
        self.stat_boxes.append(StatBoxUtil.create_traffic_box(self.view, StatBoxDataSupplier.IFSTAT_TX,
                                                              int(center_x - w / 2), int(center_y - h / 2), w, h,
                                                              self.intf))

    def get_selectable_color(self):
        if self.view.select_mode:
            if self in self.view.select_mode and \
                    (self.intf.status != EngineComponentStatus.RUNNING or
                     self.intf.interface_state == EngineInterfaceState.DOWN):
                return '#FFC0C0'
        return '#FFFFFF'
