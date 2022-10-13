from extensions.macvlan_extension import MacVlanServiceExtension
from gui.box import Box
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

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        if button == 1:
            self.debug = not self.debug
        elif button == 3:
            self.view.show_popup(x, y, ["This is a test"], lambda i: print(str(i)))

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
        line += 1
        if self.intf.interface_state != InterfaceState.DOWN:
            if self.intf.ifstat:
                rx_data, tx_data = self.intf.ifstat
                self.view.create_text(abs_x + self.INTERFACE_DEBUG_WIDTH / 2, abs_y + line * 14,
                                      f"RX: {NetworkUtils.format_thousands(rx_data)}B - "
                                      f"TX: {NetworkUtils.format_thousands(tx_data)}B", font="Arial 8",
                                      fill=text_color)
                line += 1
