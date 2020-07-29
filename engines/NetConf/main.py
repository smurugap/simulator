import gevent
from gevent import monkey
monkey.patch_all()
import os
import time
import threading
import Queue as queue
from netconf import server, nsmap_add
#ToDo: Dynamically identify the plugin based on model
from juniper import NetconfPlugin, SSHPlugin
from common.constants import USERNAME, PASSWORD
from common.util import register_event
from common.ipc_api import register_listener

import logging
logging.basicConfig(level=logging.DEBUG)
nsmap_add("sys", "urn:ietf:params:xml:ns:yang:ietf-system")
MYDIR = os.path.dirname(os.path.abspath(__file__))
NETCONF_EVENTS = dict()

class NetconfServer(object):
    def start(self, port=22, username=USERNAME, password=PASSWORD,
              version='18.4R2-S4', n_interfaces=48, socket=None,
              peer_prefix=None, n_peers=2, model=None):
        my_queue = queue.Queue()
        auth = SSHWrapper(username=username, password=password, queue=my_queue)
        self.plugin = NetconfPlugin(version=version, n_interfaces=n_interfaces,
                               peer_prefix=peer_prefix, n_peers=n_peers,
                               model=model)
        self.server = NetconfSSHServerWrapper(auth, port=port,
                                              server_methods=self.plugin,
                                              queue=my_queue)
        register_event('summary', NETCONF_EVENTS, self.summary)
        register_event('update', NETCONF_EVENTS, self.update)
        register_event('register', NETCONF_EVENTS, self.register)
        register_listener(socket, NETCONF_EVENTS)
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

    def summary(self, payload):
        return {'vns': {'count': 13}}

    def update(self, kv_pairs):
        for k,v in kv_pairs.items():
            setattr(self.plugin, k, v)

    def register(self, templates):
        for rpc_name, content in templates.items():
            filename = os.path.join('/tmp', rpc_name)
            with open(filename, 'w') as fd:
                fd.write(content)
            self.plugin.templates[rpc_name] = filename
            setattr(self.plugin, 'rpc_'+rpc_name, self.dynamic_rpc_fn(rpc_name))

class NetconfSSHServerWrapper(server.NetconfSSHServer):
    def __init__(self, auth, server_methods=None, port=830,
                 debug=True, queue=None):
        self.server_methods = server_methods
        self.session_id = 1
        self.session_locks_lock = threading.Lock()
        self.session_locks = {
            "running": 0,
            "candidate": 0,
        }
        self.queue = queue
        super(server.NetconfSSHServer, self).__init__(
            auth,
            port=port,
            host_key=os.path.join(MYDIR, 'id_rsa'),
            server_session_class=NetconfServerSessionWrapper,
            debug=debug)

class NetconfServerSessionWrapper(server.NetconfServerSession):
    def __init__(self, channel, nc_server, unused_extra_args, debug):
        self.server = nc_server
        sid = self.server._allocate_session_id()
        self.methods = self.server.server_methods
        super(server.NetconfServerSession, self).__init__(channel, debug, sid)
        try:
            data = self.server.queue.get(timeout=5)
        except:
            super(server.NetconfServerSession, self)._open_session(True)

class SSHWrapper(SSHPlugin, server.SSHUserPassController):
    def __init__(self, queue=None, *args, **kwargs):
        self.queue = queue
        super(SSHWrapper, self).__init__(*args, **kwargs)
