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


def main(argv: list[str]):
    if len(argv) < 1:
        print("Script requires one argument!")
        exit(1)

    engine = Engine(argv[0])
    engine.update_all_status()

    init_width = 1920
    init_height = 1080

    main_box = Box(0, 0, init_width, init_height)
    main_box.draggable = False
    main_box.resizeable = False

    interface_boxes = {}

    for node in engine.nodes.values():
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
                            service_box.add_interface_box(interface_box, interface_box.x == 0 and interface_box.y == 0)
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

    view = MainView(main_box)

    update_thread = threading.Thread(target=engine.continuous_update)
    update_thread.start()
    ifstat_threads = []
    for node in engine.nodes.values():
        for service in node.services.values():
            ifstat_thread = threading.Thread(target=lambda: engine.continuous_ifstat(service))
            ifstat_thread.start()
            ifstat_threads.append(ifstat_thread)

    view.run_ui_loop()

    TopoUtil.to_file(argv[0], engine.topo)

    engine.stop_updating = True
    update_thread.join()
    for x in ifstat_threads:
        x.join()


if __name__ == '__main__':
    main(sys.argv[1:])
