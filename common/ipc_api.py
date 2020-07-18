import gevent
from gevent import monkey; monkey.patch_all()
import socket
import os
import json
import logging
import errno

def register_listener(sockfile, events):
    try:
        os.unlink(sockfile)
    except OSError:
        if os.path.exists(sockfile):
            raise
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sockfile)
    gevent.spawn(wait_for_events, sock, callback)

def wait_for_events(sock, events):
    sock.listen(1)
    while True:
        connection, client = sock.accept()
        data = connection.recv(2048)
        if data:
            payload = json.loads(data.strip())
            event = payload.get('event', None)
            if event in events:
                logging.debug('Received %s with %s payload'%(event, payload))
                events[event](payload['payload'])
            else:
                logging.error('No such event %s registered: payload - %s'%(
                    event, payload))

def send_events(sockfile, payload, event=None):
    if event:
        dct = {'event': event, 'payload': payload}
        payload = json.dumps(dct)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sockfile)
    sock.sendall(payload.encode('utf-8'))
    sock.close()

'''
REGISTERED_EVENTS = {'test': test_callback}

def test_callback(payload):
    print 'recv payload', payload

register_listener('/tmp/test.sock', REGISTERED_EVENTS)
print 'sending event'
send_events('/tmp/test.sock', 'test')
'''
class UdpClient(object):
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.create()

    def create(self):
        family, socktype, proto, canonname, sockaddr = \
            socket.getaddrinfo(self.server, self.port, 0,
                               socket.SOCK_DGRAM, 0, 0)[0]
        s = socket.socket(family, socktype)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket = (s, sockaddr)

    def send(self, message):
        s, sockaddr = self.socket
        try:
            s.sendto(message, sockaddr)
        except socket.error as e:
            if e.args[0] == errno.EAGAIN or e.args[0] == errno.EINTR:
                pass
            else:
                raise

