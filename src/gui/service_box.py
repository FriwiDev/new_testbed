from gui.button import ButtonBar, Button
from gui.system_box import SystemBox
from live.engine_component import EngineService, EngineComponentStatus


class ServiceBox(SystemBox):
    def __init__(self, service: EngineService):
        super().__init__(service.component.gui_data.x, service.component.gui_data.y,
                         service.component.gui_data.width, service.component.gui_data.height)
        self.service = service

        gui_scale = 1
        self.button_bar = ButtonBar(self.x, self.y, 3, 3)
        self.on_off_button = Button(40 * gui_scale, 40 * gui_scale, None, "O", "Arial " + str(int(gui_scale * 20)),
                                    on_press=lambda x, y: self.on_press_on_off())
        self.ping_button = Button(40 * gui_scale, 40 * gui_scale, None, "P", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.on_press_ping())
        self.iperf_button = Button(40 * gui_scale, 40 * gui_scale, None, "S", "Arial " + str(int(gui_scale * 20)),
                                on_press=lambda x, y: self.on_press_iperf())
        self.destroy_button = Button(40 * gui_scale, 40 * gui_scale, None, "D", "Arial " + str(int(gui_scale * 20)),
                                on_press=lambda x, y: self.on_press_destroy())
        self.button_bar.add_button(self.on_off_button)
        self.button_bar.add_button(self.ping_button)
        self.button_bar.add_button(self.iperf_button)
        self.button_bar.add_button(self.destroy_button)

    def on_resize(self, width: int, height: int):
        super(ServiceBox, self).on_resize(width, height)
        self.service.component.gui_data.x = self.x
        self.service.component.gui_data.y = self.y
        self.service.component.gui_data.width = self.width
        self.service.component.gui_data.height = self.height

    def on_paint(self, offs_x: int, offs_y: int):
        if self.service.status == EngineComponentStatus.RUNNING:
            self.fill = 'white'
        else:
            self.fill = '#707070'
        super().on_paint(offs_x, offs_y)
        abs_x = self.x + offs_x
        abs_y = self.y + offs_y
        self.view.create_text(abs_x + self.width / 2, abs_y + self.height / 2 - 2, self.service.component.name)

        if self.focus:
            self.button_bar._set_view(self.view)
            self.button_bar.x = offs_x+self.x+self.width/2-self.button_bar.width/2
            self.button_bar.y = offs_y+self.y-self.button_bar.height

    def on_focus_gain(self):
        self.view.set_active_button_bar(self.button_bar)

    def on_focus_loose(self):
        if self.view.active_button_bar == self.button_bar:
            self.view.set_active_button_bar(None)

    def on_press_on_off(self):
        pass

    def on_press_ping(self):
        pass

    def on_press_iperf(self):
        pass

    def on_press_destroy(self):
        pass