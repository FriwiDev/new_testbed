from gui.system_box import SystemBox
from live.engine_component import EngineService, EngineComponentStatus


class ServiceBox(SystemBox):
    def __init__(self, service: EngineService):
        super().__init__(service.component.gui_data.x, service.component.gui_data.y,
                         service.component.gui_data.width, service.component.gui_data.height)
        self.service = service

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
