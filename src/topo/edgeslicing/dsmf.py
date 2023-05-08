import ipaddress
import logging
import threading

import networkx as nx
from aiohttp import web

from extensions.wireguard_extension_builder import WireguardExtensionBuilder
from live.engine import Engine
from live.engine_component import EngineService
from ryu_api import RyuSwitch
from topo.controller import Controller, RyuController
from topo.link import Link, LinkType
from topo.service import Service
from topo.switch import OVSSwitch

SWITCHES = ["s2", "s3", "s4", "s5", "s6", "s7", "s8"]
USE_VSWITCHES = True


class DomainSlice:
    def __init__(self, slice_id, config):
        self.config = config

        self.in_intf = config["id"]  # h1/2/3 -> s1
        self.out_intf = config["id"]  # s9 -> h4/5/6
        self.udp_port = 5000 + slice_id
        self.mpls_label_1 = 1000 + slice_id
        self.mpls_label_2 = 2000 + slice_id

        self.mpls_label_sfc_in_1 = 1100 + slice_id
        self.mpls_label_sfc_in_2 = 2100 + slice_id
        self.mpls_label_sfc_out_1 = 1200 + slice_id
        self.mpls_label_sfc_out_2 = 2200 + slice_id
        self.mpls_label_general = 9999

        self.src_name = config["src_name"]
        self.dst_name = config["dst_name"]
        self.sfc = config["sfc"]
        self.bw_max = config["bw_max"]
        self.bw_min = config["bw_min"]

        self.qos = {}


class DSMF:
    topology = nx.DiGraph()

    def __init__(self, name: str, core_controller_name: str):
        self.qos = None
        self.switches = None
        self.core_controller_name: str = core_controller_name
        self.core_controller_ip: ipaddress.ip_address or None = None
        self.core_controller: Controller or None = None
        self.app = None
        self.max_rate: int = 100000000
        self.general_slice_bw: int = self.max_rate
        self.slices = {}
        self.name: str = name
        self.engine: Engine or None = None
        self.dsmf_service: EngineService or None = None

    def start(self):
        self.slices = {}

        self.engine = Engine()
        # Force initial engine update
        self.engine.synchronize_topologies()
        self.engine.update_all_status()
        # And start polling
        update_thread = threading.Thread(target=self.engine.continuous_update)
        update_thread.start()

        # Begin working with our engine instance
        self.dsmf_service = self.engine.get_service_by_name(self.name)

        self.core_controller = self.engine.get_service_by_name(self.core_controller_name)
        if not self.core_controller:
            raise Exception(f"Could not locate core controller {self.core_controller_name}")
        self.core_controller_ip = self.core_controller.get_reachable_ip_from_other_by_subnet(self.dsmf_service)

        # Discover topology
        self.draw_topology_graph()
        self.qos = self.init_qos()
        self.switches = SWITCHES

        print("Core controller IP: " + self.core_controller_ip)
        self.add_general_slice()

    def add_general_slice(self):
        switch1 = self.engine.get_service_by_name("s1")
        switch2 = self.engine.get_service_by_name("s9")
        c0 = self.engine.get_service_by_name("c0")
        # ALl other packets are labeled for the general slice

        c0.cmd(
            f"ovs-ofctl -O OpenFlow13 add-flow {switch1} "
            f"'table=0,priority=30000 "
            f"actions=goto_table:1'")  # push_mpls:34888,set_mpls_label:{mpls_label_general},
        c0.cmd(
            f"ovs-ofctl -O OpenFlow13 add-flow {switch2} "
            f"'table=0,priority=30000 "
            f"actions=goto_table:1'")  # push_mpls:34888,set_mpls_label:{mpls_label_general},

        for s in self.switches:
            c0.cmd(
                f"ovs-ofctl -O OpenFlow13 add-flow {s} "
                f"'table=0,priority=30000 "  # ,eth_type=34888,mpls_label={mpls_label_general}
                f"actions=goto_table:1'")

    """Northbound API - to ESMF"""

    def start_api(self):
        port = 10000
        self.app = web.Application()
        self.app.router.add_routes([web.get('/info', self.get_info),
                                    web.get('/slices/{slice_id}', self.get_slice),
                                    web.post('/slices/{slice_id}', self.put_slice),
                                    web.delete('/slices/{slice_id}', self.delete_slice),
                                    web.patch('/slices/{slice_id}', self.patch_slice),
                                    ])
        logging.basicConfig(filename="DSMF_log.log", level=logging.DEBUG)
        web.run_app(self.app, host="0.0.0.0", port=port)

    async def get_print(self, request):
        """
        :param request:
        :return: available ingress / egress nodes, functions, links.
        """
        response = {
            "border": [{"name": "s1", "connected_domain": None, "connected_le": ["h1", "h2", "h3"]},
                       {"name": "s9", "connected_domain": None, "connected_le": ["h4", "h5", "h6"]}],
            # List of domain border nodes
            "functions": {"wg": True},  # Available network functions
            "resources": {"bw_total": "100000000"}  # Available network resources not yet reserved
        }
        return web.json_response(response)

    async def get_slice(self, request):
        slice_id = request.match_info["slice_id"]
        print(f"Request for slice {slice_id} info")
        print(self.slices[int(slice_id)])
        return web.json_response(self.slices[int(slice_id)])

    async def put_slice(self, request):
        if not request.can_read_body:
            raise web.HTTPBadRequest
        data = await request.json()
        slice_id = request.match_info["slice_id"]
        print(f"Request for new slice {slice_id} with config: ")
        print(data)
        try:
            self.add_slice(data)
        except Exception as api_exception:
            raise web.HTTPForbidden
        return web.Response(text=f"Slice {slice_id} added", status=200)

    async def delete_slice(self, request):
        # TODO Why is this unimplemented?!
        return

    async def patch_slice(self, request):
        if not request.can_read_body:
            raise web.HTTPBadRequest
        data = await request.json()
        slice_id = request.match_info["slice_id"]
        if int(slice_id) not in list(self.slices.keys()):
            raise web.HTTPBadRequest
        if data["type"] == "device":
            switch1 = self.engine.get_service_by_name("s1")
            switch2 = self.engine.get_service_by_name("s9")
            print("New ext. device registration requested")
            print(data)
            self.register_ext_device(int(slice_id), data["src"], data["dst"], switch1, switch2)
            print("Registration complete")
            return web.HTTPOk

    def draw_topology_graph(self):
        print(f"Drawing topology\n")
        self.ryu_rest = RyuSwitch()
        self.ryu_rest.API = f"http://{self.core_controller_ip}:8080"
        self.ryu_rest.DPID = self.ryu_rest.get_switches()[0]
        switches = []
        for s in self.ryu_rest.topo_get_switches():
            if len(s['ports']) > 0:
                attr = {'name': s['ports'][0]['name'].split("-")[0],
                        'vswitches': {},
                        'ext_connections': {},
                        'base_functions': {'name': "Switch", 'available': True},
                        'functions': {"enc": False, "dec": False, "monitoring": False, "auth": False},
                        'qos': {"dpid": None, "intf": None, "queues": {}}
                        }
                switches.append((s['dpid'], attr))

        hosts = [h['dpid'] for h in self.ryu_rest.topo_get_hosts()]
        # print("TOPOLOGY LINKS:")
        # print(self.ryu_rest.topo_get_links())
        links = []
        for link in self.ryu_rest.topo_get_links():
            links.append((link['src']['dpid'],
                          link['dst']['dpid'],
                          {'name': f"{link['src']['name']}<->{link['dst']['name']}",
                           'src_name': link['src']['name'],
                           'dst_name': link['dst']['name'],
                           'src_port': f"{link['src']['port_no']}",
                           'dst_port': f"{link['dst']['port_no']}",
                           'physical': True,
                           # 'bandwidth': f"{link[""]}"
                           },
                          )
                         )
            links.append((link['dst']['dpid'],
                          link['src']['dpid'],
                          {'name': f"{link['src']['name']}<->{link['dst']['name']}",
                           'dst_name': link['src']['name'],
                           'src_name': link['dst']['name'],
                           'dst_port': f"{link['src']['port_no']}",
                           'src_port': f"{link['dst']['port_no']}",
                           'slice_name': "transport",
                           'physical': True,
                           # 'bandwidth': f"{link[""]}"
                           },
                          )
                         )

        self.topology.add_nodes_from(switches)
        self.topology.add_nodes_from(hosts)
        self.topology.add_edges_from(links)
        # print(hosts)
        # print(switches)
        # print(links)
        # print(self.topology.nodes)
        # nx.write_graphml(self.topology, "./Graph/Graph")

    def register_ext_device(self, slice_id: int, src_name: str, dst_name: str, switch1: EngineService,
                            switch2: EngineService):
        c0 = self.engine.get_service_by_name("c0")
        src = self.engine.get_service_by_name(src_name)
        dst = self.engine.get_service_by_name(dst_name)

        src_ip = src.get_reachable_ip_from_other_by_subnet(dst)
        dst_ip = dst.get_reachable_ip_from_other_by_subnet(src)

        print("register_ext_device")

        s = self.slices[slice_id]

        queue = f",set_queue:4{slice_id}"
        pop_queue = ",pop_queue"

        # Label slice packets on ingress
        c0.cmd_print(
            f"ovs-ofctl -O OpenFlow13 add-flow {switch1} "
            f"'table=0,priority=38000,in_port={s.in_intf},ip,udp,nw_src={src_ip},nw_dst={dst_ip},tp_dst={s.udp_port}, "
            f"actions=push_mpls:34888,set_mpls_label:{s.mpls_label_1}{queue},output=4{pop_queue}'")
        c0.cmd_print(
            f"ovs-ofctl -O OpenFlow13 add-flow {switch2} "
            f"'table=0,priority=38000,in_port={s.out_intf},ip,udp,nw_src={dst_ip},nw_dst={src_ip},tp_dst={s.udp_port}, "
            f"actions=push_mpls:34888,set_mpls_label:{s.mpls_label_2}{queue},output=4{pop_queue}'")  # label2

        # Egress slice packets and remove label
        c0.cmd_print(
            f"ovs-ofctl -O OpenFlow13 add-flow {switch2} "
            f"'table=0,priority=38000,in_port=4,eth_type=34888,mpls_label={s.mpls_label_1}, "
            f"actions=pop_mpls:0x0800,output:{s.out_intf}'")
        c0.cmd_print(
            f"ovs-ofctl -O OpenFlow13 add-flow {switch1} "
            f"'table=0,priority=38000,in_port=4,eth_type=34888,mpls_label={s.mpls_label_2}, "  # label 2
            f"actions=pop_mpls:0x0800,output:{s.in_intf}'")

    def add_slice(self, config: dict):
        c0 = self.engine.get_service_by_name("c0")

        slice = DomainSlice(config["id"], config)
        self.slices[int(config["id"])] = slice

        slice_id = config["id"]
        src_name = config["src_name"]
        dst_name = config["dst_name"]
        sfc = config["sfc"]
        bw_max = config["bw_max"]

        # Slice 2 Control

        udp_port = 5000 + slice_id
        mpls_label_1 = 1000 + slice_id
        mpls_label_2 = 2000 + slice_id

        mpls_label_sfc_in_1 = 1100 + slice_id
        mpls_label_sfc_in_2 = 2100 + slice_id
        mpls_label_sfc_out_1 = 1200 + slice_id
        mpls_label_sfc_out_2 = 2200 + slice_id
        mpls_label_general = 9999

        # Domain Border Switches
        switch1 = self.engine.get_service_by_name("s1")
        switch2 = self.engine.get_service_by_name("s9")

        queue = f",set_queue:4{slice_id}"
        pop_queue = ",pop_queue"

        self.engine.begin_topology_changes()
        sc = self.new_controller(slice_id, domain_id=1)
        self.add_slice_switches(transport_switches=self.switches, slice_controller=sc, slice_id=slice_id)
        self.engine.flush_topology_changes()

        self.slice_qos(config, slice_id)

        for s in self.switches:
            transport_switch = self.engine.get_service_by_name(s)

            queue1 = f",set_queue:1{slice_id}"
            queue2 = f",set_queue:2{slice_id}"

            if USE_VSWITCHES:

                slice_switch = self.engine.get_service_by_name(f"{s}0{slice_id}")
                slice_intf1 = transport_switch.connectionsTo(slice_switch)[0][0].name  # TODO
                slice_intf2 = transport_switch.connectionsTo(slice_switch)[1][0].name

                self.add_traffic_policy(c0, slice_intf1, bw_max, (bw_max * 10))

                self.add_traffic_policy(c0, slice_intf1, bw_max, (bw_max * 10))

                slice_port1 = transport_switch.intfNames().index(slice_intf1)  # TODO
                slice_port2 = transport_switch.intfNames().index(slice_intf2)

                # Send packets to slice switch
                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=38000,in_port=1,ip,eth_type=34888,mpls_label={mpls_label_1} "
                    f"actions=pop_mpls:0x0800,output:{slice_port1}'")
                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=38000,in_port=2,ip,eth_type=34888,mpls_label={mpls_label_2} "  # label 2
                    f"actions=pop_mpls:0x0800,output:{slice_port2}'")

                # Slice Switch Flows

                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {slice_switch} "
                    f"'table=0,priority=38000,udp,in_port=1 "
                    f"actions=output:2'")
                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {slice_switch} "
                    f"'table=0,priority=38000,udp,in_port=2 "
                    f"actions=output:1'")
                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {slice_switch} "
                    f"'table=0,priority=30000 "
                    f"actions=drop'")

                # Handle Packets from slice switch

                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=30000,in_port={slice_port1} "
                    f"actions=drop'")

                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=30000,in_port={slice_port2} "
                    f"actions=drop'")

                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=38000,in_port={slice_port1},udp "
                    f"actions=push_mpls:34888,set_mpls_label:{mpls_label_2},{queue1},output:1{pop_queue}'")  # label 2

                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=38000,in_port={slice_port2},udp "
                    f"actions=push_mpls:34888,set_mpls_label:{mpls_label_1}{queue2},output:2{pop_queue}'")

            else:
                # Forward packets based on MPLS label to next virtual domain switch
                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=37000,in_port=1,ip,eth_type=34888,mpls_label={mpls_label_1} "
                    f"actions={queue2},output:2{pop_queue}'")
                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=37000,in_port=2,ip,eth_type=34888,mpls_label={mpls_label_2} "  # label 2
                    f"actions={queue1},output:1{pop_queue}'")

                c0.cmd(
                    f"ovs-ofctl -O OpenFlow13 add-flow {transport_switch} "
                    f"'table=0,priority=30000 "  # ,eth_type=34888,mpls_label={mpls_label_general}
                    f"actions=goto_table:1'")
        # Set up egress SFC
        if len(sfc) > 0:
            self.add_vnf_flows(slice_id, sfc, mpls_label_sfc_out_1, mpls_label_1, slice.src_name, slice.dst_name,
                               udp_port)
            # set egress flow label on border interface

            # TODO What is this magic again?! Practically all hardcoded :/
            border_switch = "s3"
            if slice_id == 1:
                slice_egress_interface = "6"
            elif slice_id == 2:
                slice_egress_interface = "8"
            else:
                slice_egress_interface = "0"

            c0.cmd(
                f"ovs-ofctl -O OpenFlow13 add-flow {border_switch} "
                f"'table=0,priority=38000,in_port={slice_egress_interface},udp "
                f"actions=push_mpls:34888,set_mpls_label:{mpls_label_sfc_out_1},resubmit:1'")

    def new_controller(self, slice_id: int, domain_id: int) -> RyuController:
        controller = RyuController(f"con_sid{slice_id}did{domain_id}", self.dsmf_service.component.executor,
                                   script_path="ryu.app.simple_switch_13")
        self.engine.altered_topo.add_service(controller)
        return controller

    def new_slice_switch(self, node_name: str, slice_id: int, controller: RyuController) -> OVSSwitch:
        """
        Start a new virtual switch
        """
        switch = OVSSwitch(f"sw_{node_name}sid{slice_id}", self.dsmf_service.component.executor,
                           controllers=[controller])
        self.engine.altered_topo.add_service(switch)
        return switch

    def add_slice_switches(self, transport_switches: [str], slice_controller: RyuController, slice_id: int):
        print("Add slice switch")
        for s in transport_switches:
            new = self.new_slice_switch(s, slice_id, slice_controller)
            switch = self.engine.altered_topo.get_service(s)
            self.engine.altered_topo.add_link(Link(self.engine.altered_topo,
                                                   new,
                                                   switch,
                                                   LinkType.VXLAN))

    def add_vnf_flows(self, slice_id, sfc, mpls_label_sfc: int, mpls_label_normal: int, src_name: str, dst_name: str,
                      udp_port: int):
        print(f"ADDING VNFs\n")
        src = self.engine.altered_topo.get_service(src_name)
        dst = self.engine.altered_topo.get_service(dst_name)

        for vnf in sfc:
            print(f"Adding VNF {vnf}\n")
            if vnf["direction"] == 1 and vnf["type"] == "wg":
                self.add_wireguard_tunnel(slice_id, src, dst, self.engine.altered_topo.get_service(vnf["entry"]),
                                          self.engine.altered_topo.get_service(vnf["exit"]),
                                          mpls_label_sfc,
                                          mpls_label_normal, udp_port)
            elif vnf["direction"] == 2 and vnf["type"] == "wg":
                self.add_wireguard_tunnel(slice_id, src, dst, self.engine.altered_topo.get_service(vnf["entry"]),
                                          self.engine.altered_topo.get_service(vnf["exit"]),
                                          mpls_label_sfc,
                                          mpls_label_normal, udp_port)
            else:
                raise NotImplementedError

    def add_wireguard_tunnel(self, slice_id: int, src: Service, dst: Service, tunnel_entrance: Service,
                             tunnel_exit: Service, mpls_label_sfc: int, mpls_label_normal: int, udp_port: int):
        c0 = self.engine.get_service_by_name("c0")

        entrance_ip = f"192.168.17{slice_id}.1"
        exit_ip = f"192.168.17{slice_id}.2"
        entrance_dev_name = f"wg0sid{slice_id}"
        exit_dev_name = f"wg1sid{slice_id}"

        intf1 = None
        intf2 = None
        for l in tunnel_entrance.intfs:
            if l.other_end_service == tunnel_exit:
                intf1 = l
                intf2 = l.other_end

        if not intf1 or not intf2:
            raise Exception(f"Other side {tunnel_exit} is not reachable from {tunnel_entrance}")

        WireguardExtensionBuilder(tunnel_entrance, tunnel_exit, intf1, intf2,
                                  entrance_ip, exit_ip, f"192.168.17{slice_id}.0/24", dev_name1=entrance_dev_name,
                                  dev_name2=exit_dev_name) \
            .build()

        # TODO Make sure that we already applied the changes when we get here

        src_live = self.engine.get_service_by_name(src.name)
        dst_live = self.engine.get_service_by_name(dst.name)
        src_ip = src_live.get_reachable_ip_from_other_by_subnet(dst_live)
        dst_ip = dst_live.get_reachable_ip_from_other_by_subnet(src_live)
        src_mac = src_live.intfs.values()[0].live_mac  # TODO Assumes every host uses only one interface
        dst_mac = dst_live.intfs.values()[0].live_mac

        c0.cmd(f"ovs-ofctl -O OpenFlow13 add-flow s3 'table=0,priority=40001,"
               f"in_port=1,ip,eth_type=34888,mpls_label={mpls_label_sfc}, "
               f"actions=pop_mpls:0x800,"
               f"set_field:{entrance_ip}->ip_dst,"
               f"set_field:{self.engine.get_service_by_name(tunnel_entrance.name).infs[entrance_dev_name].live_mac}->eth_dst,"
               f"output:{2 + slice_id}'")

        c0.cmd(f"ovs-ofctl -O OpenFlow13 add-flow s7 'table=0,priority=40001,"
               f"in_port={2 + slice_id},ip,udp,ip_dst={dst_ip} "
               f"actions="
               f"set_field:{dst_ip}->nw_dst,"
               f"set_field:{dst_mac}->dl_dst,"
               f"set_field:{src_ip}->nw_src,"
               f"set_field:{src_mac}->dl_src,"
               f"set_field:{udp_port}->udp_dst,"
               f"push_mpls:34888,set_mpls_label:{mpls_label_normal},"
               f"output:2'")

        c0.cmd(f"ovs-ofctl -O OpenFlow13 add-flow s3 "
               f"'table=0,priority=40000,in_port={2 + slice_id},ip,udp, "
               f"actions=goto_table:1'")
        c0.cmd(f"ovs-ofctl -O OpenFlow13 add-flow s7 "
               f"'table=0,priority=40000,in_port={2 + slice_id},ip,udp, "
               f"actions=goto_table:1'")

    def add_queue(self, intf: int, slice_id: int, qos_dpid: int, bw_max: int, bw_min: int, prio: int):
        c0 = self.engine.get_service_by_name("c0")
        queue = c0.cmd_print(
            f"ovs-vsctl add QoS {qos_dpid} queues {intf}{slice_id}=@newq "
            f"-- --id=@newq create queue other-config:min-rate={bw_min} other-config:max-rate={bw_max} other_config:priority={prio}"
        )
        return queue

    def set_queue_rate(self, queue_dpid: int, bw_max: int, bw_min: int):
        c0 = self.engine.get_service_by_name("c0")
        c0.cmd(f"ovs-vsctl -- set Queue {queue_dpid} other_config:max-rate={bw_max}")
        c0.cmd(f"ovs-vsctl -- set Queue {queue_dpid} other_config:min-rate={bw_min}")

        self.add_traffic_policy(c0, 's4-eth3', bw_max, bw_min)  # TODO Seems like an argument misalignment?!
        # TODO 2: Replace s4-eth3 with actually wanted traffic policy

    def add_traffic_policy(self, c0: EngineService, interface: str, rate: int, burst: int):
        # Ingress Rate Limiting, BW in bit/s
        c0.cmd(f"ovs-vsctl set interface {interface} ingress_policing_rate={rate} ingress_policing_burst={burst}")

    def slice_qos(self, config: dict, slice_id: int):
        switches = SWITCHES
        self.general_slice_bw -= config["bw_max"]

        # S1
        switch = "s1"
        intf = 4
        queue = self.add_queue(intf, slice_id, self.qos[f"{switch}-eth{intf}"]["dpid"], config["bw_max"],
                               config["bw_min"], config["prio"])
        self.qos[f"{switch}-eth{intf}"]["queues"][f"{intf}{slice_id}"] = queue
        self.set_queue_rate(self.qos[f"{switch}-eth{intf}"]["queues"]["0"], bw_max=self.general_slice_bw, bw_min=0)

        # S9
        switch = "s9"
        intf = 4
        queue = self.add_queue(intf, slice_id, self.qos[f"{switch}-eth{intf}"]["dpid"], config["bw_max"],
                               config["bw_min"], config["prio"])
        self.qos[f"{switch}-eth{intf}"]["queues"][f"{intf}{slice_id}"] = queue
        self.set_queue_rate(self.qos[f"{switch}-eth{intf}"]["queues"]["0"], bw_max=self.general_slice_bw, bw_min=0)

        # S2 - S8
        for switch in switches:
            intf = 1
            queue = self.add_queue(intf, slice_id, self.qos[f"{switch}-eth{intf}"]["dpid"], config["bw_max"],
                                   config["bw_min"], config["prio"])
            self.qos[f"{switch}-eth{intf}"]["queues"][f"{intf}{slice_id}"] = queue
            self.set_queue_rate(self.qos[f"{switch}-eth{intf}"]["queues"]["0"], bw_max=self.general_slice_bw, bw_min=0)

            intf = 2
            queue = self.add_queue(intf, slice_id, self.qos[f"{switch}-eth{intf}"]["dpid"], config["bw_max"],
                                   config["bw_min"], config["prio"])
            self.qos[f"{switch}-eth{intf}"]["queues"][f"{intf}{slice_id}"] = queue
            self.set_queue_rate(self.qos[f"{switch}-eth{intf}"]["queues"]["0"], bw_max=self.general_slice_bw, bw_min=0)

        print(self.qos)

    def add_qos(self, switch: str, intf: str, max_rate: int, bw_min: int, bw_max: int):
        c0 = self.engine.get_service_by_name("c0")
        dpids = c0.cmd_print(
            f"ovs-vsctl -- set port {switch}-eth{intf} qos=@newqos "  # TODO Change to actual ports in our test setup
            f"-- --id=@newqos create QoS type=linux-htb other-config:max-rate={max_rate} queues=0=@q0 "
            f"-- --id=@q0 create queue other-config:min-rate={bw_min} other-config:max-rate={bw_max} other_config:priority=3 ")
        return dpids.split("\r\n")

    def init_qos(self):
        qos = {}
        switches = SWITCHES
        max_rate = self.max_rate

        intf = "4"

        # S1
        dpids = self.add_qos("s1", intf, max_rate, bw_min=0, bw_max=max_rate)
        qos["s1-eth4"] = {"dpid": dpids[0], "queues": {}}
        qos["s1-eth4"]["queues"]["0"] = dpids[1]

        # S9
        dpids = self.add_qos("s9", intf, max_rate, bw_min=0, bw_max=max_rate)
        qos["s9-eth4"] = {"dpid": dpids[0], "queues": {}}
        qos["s9-eth4"]["queues"]["0"] = dpids[1]

        # S2 - S8
        for s in switches:
            intf = "1"
            dpids = self.add_qos(s, intf, max_rate, bw_min=0, bw_max=max_rate)
            qos[f"{s}-eth{intf}"] = {"dpid": dpids[0], "queues": {}}
            qos[f"{s}-eth{intf}"]["queues"]["0"] = dpids[1]

            intf = "2"
            dpids = self.add_qos(s, intf, max_rate, bw_min=0, bw_max=max_rate)
            qos[f"{s}-eth{intf}"] = {"dpid": dpids[0], "queues": {}}
            qos[f"{s}-eth{intf}"]["queues"]["0"] = dpids[1]

        return qos

    # REMOVED CODE
    # def run_eval(self):
    #   self.net.pingAll()
    #   add_slice(net=net, src_name="h2", dst_name="h4", enc_name="h10", dec_name="h9", port=5001, switch="s4",
    #          in_intf=1, out_intf=2, enc_intf=3, dec_intf=4)
    #
    # def add_vswitches(self, slice_id, controller, topo):
    #    """
    #    Add virtual switches and links to the network nodes.
    #    """
    #    switches = []
    #    # Start new vswitches on each node
    #    for node_key in self.topology.nodes:
    #        node_name = self.topology.nodes[node_key]['name']  # TODO This needs to be investigated
    #        node: OVSSwitch = self.engine.get_service_by_name(node_name)
    #        current = self.new_vswitch(node_name, slice_id, controller)
#
#        # Every vswitch gets one virtual port with corresponding port on the transport switch for each other vswitch
#        for target_key in self.topology.neighbors(node_key):
#            target_name = self.topology.nodes[target_key]['name']
#            target = self.net.get(target_name)
#            link = self.net.addLink(node1=node_name, node2=current)
#            # MPLS Labeling allows nodes to identify the correct virtual port for incoming packets
#            # phy_port = node.ports[node.connectionsTo(self.net.get(target_name))[0][0]]
#            phy_port = int(self.topology[node_key][target_key]['src_port'])
#            self.topology.nodes[node_key]['vswitches'][slice_id] = current
#            self.add_vswitch_flows(node.ports[link.intf1], node_key, slice_id, phy_port)
#        switches.append(current)
#    return switches
#
# def add_snf(self):
#    print("Add snf")
#    raise NotImplementedError
#
# def add_dnf(self, type, transport_switch, host):
#    """
#    Add a domain network function as specified in a slice configuration
#    """
#    if type not in ["wg", "monitor"]:
#        raise NotImplementedError
#
#    if type == "wg":
#        print("Add dnf: wireguard")
#
#    elif type == "monitor":
#        print("Add dnf: network monitor")
#        h = self.net.get(host)
#        h.Popen(['xterm',
#                 '-e',
#                 "udp_forwarding_server.py"])
#    else:
#        raise NotImplementedError
#
# def vnf_in_flow(self, src, dst, vnf, mpls_label, switch_port):
#    return (f"ovs-ofctl -O OpenFlow13 add-flow {vnf['switch']} 'table=0,priority=40000,"
#            f"in_port={switch_port},ip,eth_type=34888,mpls_label={mpls_label} "
#            f"actions=pop_mpls:0x800,"
#            f"set_field:{vnf['ip']}->ip_dst,"
#            f"set_field:{vnf['mac']}->eth_dst,"
#            f"output:{vnf['intf']}'")
#
# def vnf_out_flow(self, src, dst, vnf, mpls_label, switch_port, udp_port):
#    return (f"ovs-ofctl -O OpenFlow13 add-flow {vnf['switch']} "
#            f"'table=0,priority=40000,in_port={vnf['intf']},ip,udp, "
#            f"actions="
#            f"set_field:{dst.IP()}->nw_dst,"
#            f"set_field:{dst.MAC()}->dl_dst,"
#            # f"set_field:{src.IP()}->nw_src,"
#            f"set_field:{src.MAC()}->dl_src,"
#            # f"set_field:{udp_port}->udp_dst,"
#            f"push_mpls:34888,set_mpls_label:{mpls_label},"
#            f"output:2'")
