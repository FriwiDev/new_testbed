import sys
import threading

from screeninfo import get_monitors

from extensions.macvlan_extension import MacVlanServiceExtension
from extensions.wireguard_extension import WireguardServiceExtension
from gui.box import Box
from gui.interface_box import InterfaceBox
from gui.main_view import MainView
from gui.service_box import ServiceBox
from live.engine import Engine
from live.engine_topology_change_listener import EngineTopologyChangeListener
from topo.node import Node
from topo.service import Service
from topo.topo import TopoUtil, Topo


class Gui(EngineTopologyChangeListener):
    def __init__(self, argv: typing.List[str]):
        self.argv = argv

        fullscreen = "-f" in argv or "--fullscreen" in argv

        self.max_width = 0
        self.max_height = 0

        for m in get_monitors():
            if m.width > self.max_width:
                self.max_width = m.width
            if m.height > self.max_height:
                self.max_height = m.height

        self.canvas_width = 4000
        self.canvas_height = 2200
        self.init_width = self.canvas_width - self.max_width
        self.init_height = self.canvas_height - self.max_height

        self.topo_def = argv[0]
        self.engine = Engine(self.topo_def)
        self.engine.engine_topology_change_listeners.append(self)
        self.engine.update_all_status()

        self.view = MainView(self.engine, self, fullscreen)
        self.view.gui_scale = self.max_height / 1080  # 1K is standard scale

        gui_box = Box(-self.canvas_width, -self.canvas_height,
                      self.canvas_width * 2 + self.max_width, self.canvas_height * 2 + self.max_height)
        gui_box.draggable = False
        gui_box.resizeable = False

        has_data = self.engine.topo.gui_data_attachment and self.engine.topo.gui_data_attachment.x != -1
        if has_data:
            self.view.zoom_goal = self.engine.topo.gui_data_attachment.zoom
        self.view.zoom = self.view.zoom_goal * self.view.gui_scale / 100
        self.view.zoom_factor_button.text = self.view.zoom_text()

        self.main_box = Box(
            self.engine.topo.gui_data_attachment.x if has_data else
            int((self.canvas_width + self.view.width / self.view.zoom) / 2),
            self.engine.topo.gui_data_attachment.y if has_data else
            int((self.canvas_height + self.view.height / self.view.zoom) / 2),
            self.canvas_width, self.canvas_height)
        self.main_box.draggable = True
        self.main_box.resizeable = False
        self.main_box.available_bounding_boxes = [(0, 0, gui_box.width, gui_box.height, 0)]
        self.main_box.current_box = (0, 0, gui_box.width, gui_box.height, 0)

        self.view.set_box(gui_box)

        gui_box.add_box(self.main_box)

        self.update_boxes()

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

        # Flush interface changes
        self.engine.topo.gui_data_attachment.x = self.main_box.x
        self.engine.topo.gui_data_attachment.y = self.main_box.y
        self.engine.topo.gui_data_attachment.zoom = self.view.zoom_goal
        self.flush_changes(self.view.box)

        TopoUtil.to_file(self.topo_def, self.engine.topo)

        self.engine.stop_updating = True
        update_thread.join()
        for x in ifstat_threads:
            x.join()

    def flush_changes(self, box: Box):
        if isinstance(box, InterfaceBox):
            box.rebuild_gui_data()
        elif isinstance(box, ServiceBox):
            box.rebuild_gui_data()

        for b in box.subboxes:
            self.flush_changes(b)

        self.engine.write_topology_to_all(self.engine.topo)

    def update_boxes(self):
        self.main_box.clear_boxes()

        interface_boxes = {}

        for node in self.engine.nodes.values():
            for service in node.services.values():
                service_box = ServiceBox(service, self.view)
                service_box.available_bounding_boxes = [(0, 0, self.init_width, self.init_height, 0)]
                service_box.current_box = (0, 0, self.init_width, self.init_height, 0)
                self.main_box.add_box(service_box)
                for intf in service.intfs.values():
                    interface_box = InterfaceBox(intf, self.view)
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
        pass

    def on_topology_change(self, old_topo: Topo, new_topo: Topo):
        self.update_boxes()

    def on_component_change(self, old_component: Service or Node or None, new_component: Service or Node or None):
        pass


def main(argv: typing.List[str]):
    if len(argv) < 1:
        print("Script requires one argument!")
        exit(1)

    # Start gui
    Gui(argv).run()


if __name__ == '__main__':
    main(sys.argv[1:])
