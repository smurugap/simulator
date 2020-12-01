import gevent
from gevent import monkey
monkey.patch_all()
import subprocess
import os
import signal
import time
import threading
import Queue as queue
from netconf import server, nsmap_add
#ToDo: Dynamically identify the plugin based on model
from engines.netconf.juniper import NetconfPlugin, SSHPlugin
from common.constants import USERNAME, PASSWORD
from common.util import register_event, nc_elem2dict
from common.ipc_api import register_listener

import logging
logging.basicConfig(level=logging.DEBUG)
nsmap_add("sys", "urn:ietf:params:xml:ns:yang:ietf-system")
MYDIR = os.path.dirname(os.path.abspath(__file__))
DIC = os.path.join(MYDIR, 'dic.py')
TEMPLATE_DIR = os.path.join(MYDIR, 'templates')
NETCONF_EVENTS = dict()

from lxml import etree

class NetconfServer(object):
    def __init__(self, port=22, username=USERNAME, password=PASSWORD,
              version='18.4R2-S4', model=None, n_interfaces=48,
              peers=None, manager=None, secret=None, device_id=None,
              socket=None):
        self.socket = socket
        self.port = port
        self.queue = queue.Queue()
        self.auth = SSHWrapper(username=username,
            password=password, queue=self.queue)
        self.plugin = NetconfPlugin(version=version, peers=peers,
            n_interfaces=n_interfaces, model=model, socket=socket)
        self.onboard_templates()
        self.manager = manager
        self.device_id = device_id
        self.secret = secret
        self.start_dic()

    def start_dic(self):
        self.dic_pid = None
        if self.manager and self.device_id and self.secret:
            proc = subprocess.Popen(
                'python %s --manager %s --secret %s --device_id %s'%(
                DIC, self.manager, self.secret, self.device_id), shell=True)
            self.dic_pid = proc.pid

    def start(self):
        self.server = server.NetconfSSHServer(self.auth,
            port=self.port, server_methods=self.plugin,
            host_key=os.path.join(MYDIR, 'id_rsa'),
            debug=True, queue=self.queue)
        register_event('summary', NETCONF_EVENTS, self.summary)
        register_event('update', NETCONF_EVENTS, self.update)
        register_event('register', NETCONF_EVENTS, self.register)
        register_event('dic', NETCONF_EVENTS, self.dic_callback)
        register_listener(self.socket, NETCONF_EVENTS)
        try:
            while True:
                time.sleep(1)
        except:
            pass
        self.close()

    def close(self):
        self.server.close()

    def dynamic_rpc_fn(self, rpc_name):
        def wrapper(session, rpc, *args, **kwargs):
            kwargs = dict()
            rformat = rpc.getchildren()[0].get('format')
            if rformat == 'json':
                kwargs['rtype'] = 'json'
            return self.plugin._convert_template(rpc_name, **kwargs)
        return wrapper

    def dic_callback(self, payload):
        manager = payload['manager']
        device_id = payload['device_id']
        secret = payload['secret']
        if manager != self.manager or \
           device_id != self.device_id or \
           secret != self.secret:
            if self.dic_pid:
                os.kill(self.dic_pid, signal.SIGTERM)
                self.dic_pid = None
            self.manager = manager
            self.device_id = device_id
            self.secret = secret
            self.start_dic()

    def summary(self, payload):
        return self.plugin.summary(payload)

    def update(self, kv_pairs):
        for k,v in kv_pairs.items():
            if type(getattr(self.plugin, k, None)) is dict:
                getattr(self.plugin, k).update(v)
                continue
            setattr(self.plugin, k, v)

    def register(self, templates):
        for rpc_name, content in templates.items():
            rpc_name = rpc_name.replace("-", "_")
            if not rpc_name.startswith('rpc_'):
                rpc_name = "rpc_"+rpc_name
            filename = os.path.join(TEMPLATE_DIR, rpc_name)
            with open(filename, 'w') as fd:
                fd.write(content)
            self.plugin.templates[rpc_name] = filename
            setattr(self.plugin, rpc_name, self.dynamic_rpc_fn(rpc_name))

    def onboard_templates(self):
        for file in os.listdir(TEMPLATE_DIR):
            if file.startswith('rpc_'):
                self.plugin.templates[file] = os.path.join(TEMPLATE_DIR, file)
                setattr(self.plugin, file, self.dynamic_rpc_fn(file))

class SSHWrapper(SSHPlugin, server.SSHUserPassController):
    pass
