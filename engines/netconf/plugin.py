from common.docker_api import docker_h
from common.ipc_api import send_event
from common.util import get_random_mac
from netconf import util, NSMAP
from datetime import datetime
from jinja2 import Template, Environment, meta
from lxml import etree
from engines.netconf import summarize
import time
import re

IGNORE_KEYWORDS = ['range']

class NetconfPluginBase(object):
    def __init__(self, version='18.4R2-S4', n_interfaces=48,
                 peers=2, model='qfx10002-36q', socket=None):
        self.version = version
        self.n_interfaces = n_interfaces
        self.peers = peers
        self.model = model
        self.socket = socket
        self.hostname = docker_h.my_hostname
        self.my_index = docker_h.my_index
        self.tunnel_ip = docker_h.my_ip
        self.macaddr = get_random_mac()
        self._config_files = list()
        self.rollback_count = 10

    def update_dic(self, manager, secret, device_id):
        payload = {'manager': manager, 'secret': secret, 'device_id': device_id}
        send_event(self.socket, 'dic', payload)

    def parse_dic(self, configs):
        manager = secret = device_id = None
        for line in configs.splitlines():
            if 'outbound-ssh' not in line:
                continue
            if 'device-id' in line:
                pattern = '.*device-id (?P<device_id>\S+)'
                match = re.match(pattern, line)
                device_id = match.group('device_id')
            if 'secret' in line:
                pattern = '.*secret (?P<secret>\S+)'
                match = re.match(pattern, line)
                secret = match.group('secret')
            if 'port' in line:
                pattern = '.*outbound-ssh.* (?P<manager>\S+) port (?P<port>\d+)'
                match = re.match(pattern, line)
                manager = match.group('manager')
        self.update_dic(manager, secret, device_id)

    def nc_append_capabilities(self, capabilities):  # pylint: disable=W0613
        """The server should append any capabilities it supports to capabilities"""
        util.subelm(capabilities, "capability").text = "urn:ietf:params:netconf:capability:xpath:1.0"
        util.subelm(capabilities, "capability").text = NSMAP["sys"]

    def _convert_template(self, key, rtype='xml'):
        filename = self.templates[key]
        with open(filename, 'r') as fd:
            content = fd.read()
        parsed_content = Environment().parse(content)
        attrs = meta.find_undeclared_variables(parsed_content)
        kwargs = dict()
        for attr in attrs:
            if attr in IGNORE_KEYWORDS:
                continue
            kwargs[attr] = getattr(self, attr)
        template = Template(content)
        rendered = template.render(**kwargs)
        if rtype.lower() == 'xml':
            return etree.fromstring(rendered)
        elif rtype.lower() == 'raw':
            return rendered

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

    def rpc_commit(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_unlock_configuration(self, *args, **kwargs):
        reply = etree.Element('ok')
        return reply

    def rpc_load_configuration(self, session, rpc, config, *args, **kwargs):
        epoch = time.time()
        filename = os.path.join('/tmp', str(epoch))
        self._config_files.append(filename)
        if 'outbound-ssh' in config.text:
            self.parse_dic(config.text)
        with open(filename, 'w') as fd:
            fd.write(config.text)
        filename = os.path.join('/tmp', 'current_config.conf')
        with open(filename, 'w') as fd:
            fd.write(config.text)
        seconds = 10
        length = len(config.text)
        if length > 500000:
            seconds = (length/500000)*15 + 10
        time.sleep(seconds)
        reply = etree.Element('ok')
        return reply

    def check_channel_exec_request(self, *args, **kwargs):
        return True

    def summary(self, payload):
        if not self._config_files:
            return dict()
        filename = self._config_files[-1]
        obj = summarize.ParseConfig(filename)
        ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(os.path.basename(filename))))
        return {'timestamp': ctime, 'content': obj.parse()}
