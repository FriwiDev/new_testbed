from extensions.macvlan_extension import MacVlanServiceExtension
from gui.box import Box
from gui.button import ButtonBar, Button
from live.engine_component import EngineInterface, EngineComponentStatus
from network.network_utils import NetworkUtils
from ssh.ip_addr_ssh_command import InterfaceState


class InterfaceBox(Box):
    INTERFACE_DEBUG_WIDTH = 220
    INTERFACE_DEBUG_HEIGHT = 130

    def __init__(self, intf: EngineInterface):
        super().__init__(intf.component.gui_data.x, intf.component.gui_data.y,
                         intf.component.gui_data.width, intf.component.gui_data.height)
        self.intf = intf
        self.resizeable = False
        self.debug = False
        self.admin_net = isinstance(intf.extension, MacVlanServiceExtension)
        
        gui_scale = 1
        self.button_bar = ButtonBar(self.x, self.y, 3, 3)
        self.on_off_button = Button(40 * gui_scale, 40 * gui_scale, None, "O", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.on_press_on_off())
        self.debug_button = Button(40 * gui_scale, 40 * gui_scale, None, "i", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.on_press_debug())
        self.rx_button = Button(40 * gui_scale, 40 * gui_scale, None, "RX", "Arial " + str(int(gui_scale * 20)),
                 on_press=lambda x, y: self.on_press_rx_button())
        self.tx_button = Button(40 * gui_scale, 40 * gui_scale, None, "TX", "Arial " + str(int(gui_scale * 20)),
                                on_press=lambda x, y: self.on_press_tx_button())
        self.button_bar.add_button(self.on_off_button)
        self.button_bar.add_button(self.debug_button)
        self.button_bar.add_button(self.rx_button)
        self.button_bar.add_button(self.tx_button)

    def on_resize(self, width: int, height: int):
        super(InterfaceBox, self).on_resize(width, height)
        self.intf.component.gui_data.x = self.x
        self.intf.component.gui_data.y = self.y
        self.intf.component.gui_data.width = self.width
        self.intf.component.gui_data.height = self.height

    def on_paint(self, offs_x: int, offs_y: int):
        if self.intf.status == EngineComponentStatus.RUNNING:
            if self.admin_net:
                self.fill = "#50FF50"
            else:
                self.fill = 'white'
        else:
            self.fill = '#707070'
        super().on_paint(offs_x, offs_y)
        abs_x = self.x + offs_x
        abs_y = self.y + offs_y
        angle = 0
        rot = self.get_rotation()
        if rot in [1, 3]:
            angle = 90
        self.view.create_text(abs_x + self.width / 2, abs_y + self.height / 2, self.intf.component.name,
                              font="Arial 10", angle=angle)
        if self.debug:
            if rot == 0:
                self.draw_interface_debug(abs_x + self.width / 2 - self.INTERFACE_DEBUG_WIDTH / 2,
                                          abs_y - self.INTERFACE_DEBUG_HEIGHT)
            elif rot == 3:
                self.draw_interface_debug(abs_x + self.width, abs_y + self.height / 2 - self.INTERFACE_DEBUG_HEIGHT / 2)
            elif rot in [2, -1]:
                self.draw_interface_debug(abs_x + self.width / 2 - self.INTERFACE_DEBUG_WIDTH / 2,
                                          abs_y + self.height)
            elif rot == 1:
                self.draw_interface_debug(abs_x - self.INTERFACE_DEBUG_WIDTH,
                                          abs_y + self.height / 2 - self.INTERFACE_DEBUG_HEIGHT / 2)

        if self.focus:
            self.button_bar._set_view(self.view)
            self.button_bar.x = offs_x+self.x+self.width/2-self.button_bar.width/2
            self.button_bar.y = offs_y+self.y-self.button_bar.height

    def draw_interface_debug(self, abs_x: int, abs_y: int):
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.INTERFACE_DEBUG_WIDTH,
                                          abs_y + self.INTERFACE_DEBUG_HEIGHT, fill='#505050')
        text_color = '#FFFFFF'
        line = 1
        self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                              f"{self.intf.component.name} <{self.intf.interface_state.name}>", font="Arial 8",
                              fill=text_color)
        line += 1
        if self.intf.live_mac:
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                                  f"{self.intf.live_mac}", font="Arial 8",
                                  fill=text_color)
            line += 1
        for ip, net in self.intf.live_ips:
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                                  f"{ip}/{net.prefixlen}", font="Arial 8",
                                  fill=text_color)
            line += 1
        if self.intf.tcqdisc[0] > 0:
            qdisc = f" Delay<{self.format_micro_seconds(self.intf.tcqdisc[0])}, " \
                    f"{self.format_micro_seconds(self.intf.tcqdisc[1])}, " \
                    f"{self.format_percent(self.intf.tcqdisc[2])}>"
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                                  qdisc, font="Arial 8",
                                  fill=text_color)
            line += 1
        if self.intf.tcqdisc[3] > 0:
            qdisc = f" Loss<{self.format_percent(self.intf.tcqdisc[3])}, " \
                    f"{self.format_percent(self.intf.tcqdisc[4])}>"
            self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                                  qdisc, font="Arial 8",
                                  fill=text_color)
            line += 1
        line += 1
        if self.intf.interface_state != InterfaceState.DOWN:
            if self.intf.ifstat:
                rx_data, tx_data = self.intf.ifstat
                self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                                      f"RX: {NetworkUtils.format_thousands(rx_data)}B - "
                                      f"TX: {NetworkUtils.format_thousands(tx_data)}B", font="Arial 8",
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
        pass

    def on_press_debug(self):
        self.debug = not self.debug

    def on_press_rx_button(self):
        pass

    def on_press_tx_button(self):
        pass
