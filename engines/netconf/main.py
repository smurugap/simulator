import gevent
from gevent import monkey
monkey.patch_all()
import os
import time
import threading
import Queue as queue
from netconf import server, nsmap_add
#ToDo: Dynamically identify the plugin based on model
from engines.netconf.juniper import NetconfPlugin, SSHPlugin
from engines.netconf.dic import DeviceInitiatedConnection
from common.constants import USERNAME, PASSWORD
from common.util import register_event
from common.ipc_api import register_listener

import logging
logging.basicConfig(level=logging.DEBUG)
nsmap_add("sys", "urn:ietf:params:xml:ns:yang:ietf-system")
MYDIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(MYDIR, 'templates')
NETCONF_EVENTS = dict()

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
        self.dic_greenlet = None
        if self.manager and self.device_id and self.secret:
            self.dic = DeviceInitiatedConnection((self.manager, 7804),
                ('127.0.0.1', 22), self.device_id, self.secret)
            self.dic_greenlet = gevent.spawn(self.dic.run)

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
        def wrapper(*args, **kwargs):
            return self.plugin._convert_template(rpc_name)
        return wrapper

    def dic_callback(self, payload):
        manager = payload['manager']
        device_id = payload['device_id']
        secret = payload['secret']
        if manager != self.manager or \
           device_id != self.device_id or \
           secret != self.secret:
            if self.dic_greenlet:
                gevent.kill(self.dic_greenlet)
            self.manager = manager
            self.device_id = device_id
            self.secret = secret
            self.start_dic()

    def summary(self, payload):
        return self.plugin.summary(payload)

    def update(self, kv_pairs):
        for k,v in kv_pairs.items():
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
