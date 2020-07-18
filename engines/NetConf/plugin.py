from common.docker_api import docker_h
from common.util import get_random_mac
from netconf import util, NSMAP
from datetime import datetime
from jinja2 import Template
from lxml import etree
import time

class NetconfPluginBase(object):
    def __init__(self, version='18.4R2-S4', n_interfaces=48,
                 peer_prefix=None, n_peers=2, model='qfx10002-72q'):
        self.version = version
        self.n_interfaces = n_interfaces
        self.peer_prefix = peer_prefix
        self.n_peers = n_peers
        self.model = model
        self.hostname = docker_h.my_hostname
        self.my_index = docker_h.my_index
        self.tunnel_ip = docker_h.my_ip
        self.macaddr = get_random_mac()

    def nc_append_capabilities(self, capabilities):  # pylint: disable=W0613
        """The server should append any capabilities it supports to capabilities"""
        util.subelm(capabilities, "capability").text = "urn:ietf:params:netconf:capability:xpath:1.0"
        util.subelm(capabilities, "capability").text = NSMAP["sys"]

    def _convert_template(self, key, rtype='xml', **kwargs):
        filename = self.templates[key]
        with open(filename, 'r') as fd:
            template = Template(fd.read())
        content = template.render(**kwargs)
        if rtype.lower() == 'xml':
            return etree.fromstring(content)
        elif rtype.lower() == 'raw':
            return content

    def rpc_open_configuration(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_close_configuration(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_lock_configuration(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_commit_configuration(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_unlock_configuration(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_load_configuration(self, session, rpc, config, *args, **kwargs):
        tfile = datetime.now().strftime("%Y-%m-%d-%H:%M:%S.%f")+'.conf'
        filename=os.path.join('/tmp', tfile)
        with open(filename, 'w') as fd:
            fd.write(config.text)
        filename=os.path.join('/tmp', 'current_config.conf')
        with open(filename, 'w') as fd:
            fd.write(config.text)
        seconds = (len(config.text)/500000)+15
        time.sleep(seconds)
        reply = etree.Element('ok')
        return reply

    def check_channel_exec_request(self, *args, **kwargs):
        return True
