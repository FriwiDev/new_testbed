import math
import sys
import threading

from extensions.macvlan_extension import MacVlanServiceExtension
from extensions.wireguard_extension import WireguardServiceExtension
from gui.StatBox import StatBox
from gui.box import Box
from gui.button import ButtonBar, Button
from gui.interface_box import InterfaceBox
from gui.main_view import MainView
from gui.service_box import ServiceBox
from live.engine import Engine
from topo.topo import TopoUtil


class Gui(object):
    def __init__(self, argv: list[str]):
        self.argv = argv

        gui_scale = 1
        init_width = 1920
        init_height = 980
        self.zoom = 100

        self.engine = Engine(argv[0])
        self.engine.update_all_status()

        gui_box = Box(0, 0, init_width, init_height)
        gui_box.draggable = False
        gui_box.resizeable = False

        main_box = Box(0, 0, init_width, init_height)
        main_box.draggable = True
        main_box.resizeable = False
        main_box.available_bounding_boxes = [(0, 0, init_width, init_height, 0)]
        main_box.current_box = (0, 0, init_width, init_height, 0)

        gui_box.add_box(main_box)

        zoom_box = ButtonBar(x=10 * gui_scale, y=init_height - 10 * gui_scale)
        zoom_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "-", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.zoom_out()))
        self.zoom_factor_button = Button(80 * gui_scale, 40 * gui_scale, None,
                                         self.zoom_text(), "Arial " + str(int(gui_scale * 14)),
                                         on_press=None, enabled=False, text_offs_y=int((20 - 14) / 2 * gui_scale))
        zoom_box.add_button(self.zoom_factor_button)
        zoom_box.add_button(Button(40 * gui_scale, 40 * gui_scale, None, "+", "Arial " + str(int(gui_scale * 20)),
                                   on_press=lambda x, y: self.zoom_in()))
        zoom_box.y -= zoom_box.height

        gui_box.add_box(zoom_box)

        stat = StatBox(100, 100, 200, 100)
        stat.available_bounding_boxes = [(0, 0, init_width, init_height, 0)]
        stat.current_box = (0, 0, init_width, init_height, 0)
        for i in range(0, 20):
            if i == 10:
                stat.add_value(i, math.inf)
            else:
                stat.add_value(i, i + 1)
        gui_box.add_box(stat)

        interface_boxes = {}

        for node in self.engine.nodes.values():
            for service in node.services.values():
                service_box = ServiceBox(service)
                service_box.available_bounding_boxes = [(0, 0, init_width, init_height, 0)]
                service_box.current_box = (0, 0, init_width, init_height, 0)
                main_box.add_box(service_box)
                for intf in service.intfs.values():
                    interface_box = InterfaceBox(intf)
                    if len(intf.component.links) > 0:
                        service_box.add_interface_box(interface_box, interface_box.x == 0 and interface_box.y == 0)
                    else:
                        if intf.extension:
                            if isinstance(intf.extension, WireguardServiceExtension):
                                key = (service.component.name, intf.extension.intf.name)
                                if key in interface_boxes:
                                    interface_box.add_line(interface_boxes[key], dash=(2, 1))
                                    interface_box.update_all_lines()
                            elif isinstance(intf.extension, MacVlanServiceExtension):
                                service_box.add_interface_box(interface_box,
                                                              interface_box.x == 0 and interface_box.y == 0)
                                continue
                        service_box.add_inner_box(interface_box)
                    interface_boxes[(service.component.name, intf.component.name)] = interface_box
                    for link in intf.component.links:
                        other_intf = link.intf1 if intf.component == link.intf2 else link.intf2
                        other_service = link.service1 if intf.component == link.intf2 else link.service2
                        key = (other_service.name, other_intf.name)
                        if key in interface_boxes:
                            interface_box.add_line(interface_boxes[key], dash=(2, 1))
                # TODO Find out why components shift slightly after reload
                service_box.on_resize(service_box.width, service_box.height)

        self.view = MainView(gui_box)

    def run(self):
        update_thread = threading.Thread(target=self.engine.continuous_update)
        update_thread.start()
        ifstat_threads = []
        for node in self.engine.nodes.values():
            for service in node.services.values():
                ifstat_thread = threading.Thread(target=lambda: self.engine.continuous_ifstat(service))
                ifstat_thread.start()
                ifstat_threads.append(ifstat_thread)

        self.view.run_ui_loop()

        TopoUtil.to_file(self.argv[0], self.engine.topo)

        self.engine.stop_updating = True
        update_thread.join()
        for x in ifstat_threads:
            x.join()

    def zoom_in(self):
        self.zoom += 20
        if self.zoom > 500:
            self.zoom = 500
        self.zoom_factor_button.text = self.zoom_text()

    def zoom_out(self):
        self.zoom -= 20
        if self.zoom < 20:
            self.zoom = 20
        self.zoom_factor_button.text = self.zoom_text()

    def zoom_text(self) -> str:
        return str(int(self.zoom)) + "%"


def main(argv: list[str]):
    if len(argv) < 1:
        print("Script requires one argument!")
        exit(1)

    # Start gui
    Gui(argv).run()


if __name__ == '__main__':
    main(sys.argv[1:])
