import sys
import threading

from extensions.macvlan_extension import MacVlanServiceExtension
from extensions.wireguard_extension import WireguardServiceExtension
from gui.box import Box
from gui.interface_box import InterfaceBox
from gui.main_view import MainView
from gui.service_box import ServiceBox
from live.engine import Engine
from topo.topo import TopoUtil


class Gui(object):
    def __init__(self, argv: list[str]):
        self.argv = argv

        init_width = 1920
        init_height = 980

        self.engine = Engine(argv[0])
        self.engine.update_all_status()

        self.view = MainView(self.engine)

        gui_box = Box(0, 0, init_width, init_height)
        gui_box.draggable = False
        gui_box.resizeable = False

        self.view.set_box(gui_box)

        main_box = Box(0, 0, init_width, init_height)
        main_box.draggable = True
        main_box.resizeable = False
        main_box.available_bounding_boxes = [(0, 0, init_width, init_height, 0)]
        main_box.current_box = (0, 0, init_width, init_height, 0)

        gui_box.add_box(main_box)

        interface_boxes = {}

        for node in self.engine.nodes.values():
            for service in node.services.values():
                service_box = ServiceBox(service, self.view)
                service_box.available_bounding_boxes = [(0, 0, init_width, init_height, 0)]
                service_box.current_box = (0, 0, init_width, init_height, 0)
                main_box.add_box(service_box)
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
        self.flush_changes(self.view.box)

        TopoUtil.to_file(self.argv[0], self.engine.topo)

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


def main(argv: list[str]):
    if len(argv) < 1:
        print("Script requires one argument!")
        exit(1)

    # Start gui
    Gui(argv).run()


if __name__ == '__main__':
    main(sys.argv[1:])
