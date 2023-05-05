# End to End Slice Management Function
# Receive slice request from local endpoint or corresponding ESMF, generate e2e slice configuration, instruct DSMFs
import secrets
import sys
import time

sys.path.insert(0, '/mnt/hgfs/shared_folder/venv/lib/python3.8/site-packages')
import json
import logging
import asyncio
from aiohttp import web
import requests
import networkx as nx
from cryptography.fernet import Fernet


class Domain:
    ip = "0.0.0.0"
    port = "8080"

class E2ESlice:
    """
    An end-to-end slice
    """
    domains = []  # List of domain slice management functions along the e2e slices path
    slice_id = -1
    config = {}

    def __init__(self, domains, slice_id, config):
        self.domains = domains
        self.slice_id = slice_id
        self.config = config

    """
    Southbound - Slice API
    """

    async def deploy_domain_slices(self, config):
        for d in self.domains:
            logging.info("ESMF: install_domain_slice")
            uri = f"http://0.0.0.0:10000/slices/{self.slice_id}"
            response = requests.post(url=uri, json=config)

    async def update_domain_slices(self, config):
        print("Update_domain_slice")
        for d in self.domains:
            logging.info("ESMF: update_domain_slices")
            uri = f"http://0.0.0.0:10000/slices/{self.slice_id}"
            response = requests.patch(url=uri, json=config)

    async def remove_domain_slices(self):
        logging.info("ESMF: delete_domain_slice")
        for d in self.domains:
            logging.info("ESMF: remove_domain_slices")
            uri = self.domains.nodes[d]["dsmf_at"] + f"/slices/{self.slice_id}"
            requests.delete(url=uri)


def read_json_from_file(path):
    file = open(path)
    content = json.load(file)
    file.close()
    return content


class ESMF:
    slices = {}
    app = web.Application()
    domains = nx.DiGraph()

    def __init__(self):
        self.key = Fernet.generate_key()
        self.fcrypto = Fernet(self.key)
        self.build_domains_graph()
        self.start_api()

    """
    Southbound - to DSMFs
    """

    def build_domains_graph(self):
        """
        Buod ,domain graph from domains and inte-domain links learned out-of-band.
        :return:
        """
        domain_list = read_json_from_file("domains")
        for d in domain_list:
            self.domains.add_node(d, dsmf_at=domain_list[d])
        self.update_domains()

    def update_domains(self):
        """
        Domains learned out-of-band.
        Runs info request for each known domain and adds updated info to domain graph.
        :return: Topology graph of the known domains
        """
        for n in self.domains:
            r = requests.get(url=self.domains.nodes[n]["dsmf_at"] + "/info")
            self.domains.nodes[n]["border"] = r.json()["border"]  # List of inter-domain links
            self.domains.nodes[n]["functions"] = r.json()["functions"]  # Available network functions
            self.domains.nodes[n]["resources"] = r.json()["resources"]  # Available network resources not yet reserved

    def slice_possible(self, config):
        """
        Checks, if a new slice can be established by
        comparing the requested parameters and the available domain resources
        :param config: Parameters requested for a new slice
        :return: Boolean
        """
        if self.slice_in_templates(config):
            return True
        else:
            return True

    def slice_in_templates(self, config):
        return False

    async def add_slice(self, slice_id, config):
        self.update_domains()
        new_slice = E2ESlice(self.domains, slice_id, config)
        await new_slice.deploy_domain_slices(config)
        self.slices[slice_id] = new_slice
        slice_response = {"slice_id": slice_id}
        print(f"Slice {slice_id} added")
        return slice_response

    """
    Westbound - to/from local endpoint
    """

    def start_api(self):
        port = 9000
        self.app.router.add_routes([web.post('/slices', self.handle_slice_request),
                                    web.patch('/slices/{slice_id}', self.handle_slice_update),
                                    web.delete('/slices/{slice_id}', self.handle_slice_deletion),
                                    web.get('/auth', self.handle_endpoint_auth)])
        web.run_app(self.app, host="0.0.0.0", port=port)

    async def handle_endpoint_auth(self, request):
        ip = str(request.remote)
        print(f"Auth request from {ip}")
        response = {"ip": ip, "config_token": self.slice_config_token(ip)}
        return web.json_response(response)

    async def handle_slice_request(self, request):
        """
        Handles requests for slices from local endpoints.
        Installs slice trough DSMFs.
        """
        if not request.can_read_body:
            raise web.HTTPBadRequest
        data = await request.json()
        if "config" not in data:
            raise web.HTTPBadRequest

        config = data["config"]
        slice_id = config["id"]

        slice_response = {}
        logging.info("ESMF: Received slice request")
        if self.auth_slice_request(data["token"], str(request.remote)):
            logging.info("ESMF: Request auth. successful")
            if self.slice_possible(config):
                print(f"Received slice {slice_id} request ")
                print(config)
                slice_response = await self.add_slice(slice_id, config)
                return web.json_response(data=slice_response, status=201)
            else:
                raise web.HTTPPreconditionFailed
        else:
            # Raise Exception, if slice request could not be fullfilled
            raise web.HTTPUnauthorized

    async def handle_slice_update(self, request):
        slice_id = request.match_info['slice_id']
        if not request.can_read_body or int(slice_id) not in list(self.slices.keys()):
            raise web.HTTPBadRequest
        data = await request.json()
        if not self.auth_slice_request(data["token"], str(request.remote)):
            raise web.HTTPUnauthorized
        rsp = await self.slices[int(slice_id)].update_domain_slices(data["config"])
        print(rsp)
        slice_response = {"ip": str(request.remote), "port": "5001", "slice_id": slice_id}
        return web.json_response(slice_response, status=201)

    async def handle_slice_deletion(self, request):
        print("Slice deletion requested")
        if not request.can_read_body:
            raise web.HTTPBadRequest
        data = await request.json()
        if not self.auth_slice_request(data["token"], str(request.remote)):
            raise web.HTTPUnauthorized
        slice_id = request.match_info['slice_id']
        if slice_id in list(self.slices.keys()):
            self.slices[slice_id].remove_domain_slices()
            self.slices.pop(slice_id)

    def slice_config_token(self, ip: str):
        timestamp = time.time()
        nonce = secrets.token_urlsafe(16)
        content = ip  # + nonce
        data = bytes(content, 'utf-8', 'replace')
        token = self.fcrypto.encrypt_at_time(data, int(timestamp))
        return str(token, encoding="utf-8")

    def auth_slice_request(self, token, ip):
        content = ip  # + nonce
        data = bytes(content, 'utf-8', 'replace')
        logging.info("ESMF: Verify slice auth")
        if data == self.fcrypto.decrypt_at_time(bytes(token, encoding='utf-8'), ttl=86400, current_time=int(time.time())):
            return True
        else:
            return False

    async def coro(self, timeout):
        await asyncio.sleep(timeout)

    """
    Eastbound - to secondary ESMF
    """

    def negotiate_slice(self):
        """
        Negotiate available resources for a new slice without fitting template.
        """
        logging.info("ESMF: Slice negotiation")

    def request_slice(self):
        """
        Request reservation of resources for a new slice with existing template.
        """
        logging.info("ESMF: Slice request")

    def esmf_cli(self):
        while True:
            try:
                command = input("ESMF> ")
                commands = command.split(" ")
                if commands[0] == "exit":
                    break
                elif commands[0] == "api":
                    self.start_api()
                else:
                    print("Invalid input")
            except Exception:
                logging.info(Exception)
                continue


if __name__ == "__main__":
    esmf = ESMF()
    #logging.basicConfig(level=logging.INFO)
    #logging.info("ESMF: Run")
    esmf.start_api()
    esmf.esmf_cli()

