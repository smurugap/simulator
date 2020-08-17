import socket
import logging
import logging.handlers
from common.ipc_api import register_listener
from common.util import register_event
from common.docker_api import docker_h

SYSLOG_EVENTS = dict()

class SyslogEngine(object):
    def __init__(self, server, port=514, socket=None):
        self.server, self.port, self.socket = server, port, socket
        self.logger = logging.getLogger(str(docker_h.my_hostname))
        self.logger.setLevel(logging.DEBUG)

    def send_syslog(self, payload):
        handler = logging.handlers.SysLogHandler(
            address=(self.server, int(self.port)),
            facility=payload['facility'], socktype=socket.SOCK_DGRAM)
        formatter = logging.Formatter('%(asctime)s %(name)s ' + 
            payload['facility'] + ': %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        try:
            getattr(self.logger, payload['level'])(str(payload['message']))
        finally:
            self.logger.removeHandler(handler)

    def start(self):
        register_event('send_syslog', SYSLOG_EVENTS, self.send_syslog)
        register_listener(self.socket, SYSLOG_EVENTS)
        while True:
            time.sleep(1)
