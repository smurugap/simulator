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

import logging
logging.basicConfig(level=logging.DEBUG)
nsmap_add("sys", "urn:ietf:params:xml:ns:yang:ietf-system")
MYDIR = os.path.dirname(os.path.abspath(__file__))

class NetconfServer(object):
    def start(self, port=22, username=USERNAME, password=PASSWORD,
              version='18.4R2-S4', n_interfaces=48,
              peer_prefix=None, n_peers=2, model=None):
        my_queue = queue.Queue()
        auth = SSHWrapper(username=username, password=password, queue=my_queue)
        plugin = NetconfPlugin(version=version, n_interfaces=n_interfaces,
                               peer_prefix=peer_prefix, n_peers=n_peers,
                               model=model)
        self.server = NetconfSSHServerWrapper(auth, port=port,
                                              server_methods=plugin,
                                              queue=my_queue)
        try:
            while True:
                time.sleep(1)
        except:
            pass
        self.close()

    def close(self):
        self.server.close()

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
