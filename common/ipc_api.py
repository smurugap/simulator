import socket
import os
import json
import logging
import errno
from common.util import gevent

def register_listener(sockfile, events):
    ''' Server would register the unix domain socket .sock file '''
    try:
        os.unlink(sockfile)
    except OSError:
        if os.path.exists(sockfile):
            raise
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sockfile)
    gevent.spawn(wait_for_events, sock, events)

def wait_for_events(sock, events):
    ''' Server would listen for any events on the socket '''
    sock.listen(1)
    while True:
        status = False
        connection, client = sock.accept()
        data = connection.recv(2048)
        received_data = data.decode('utf-8')
        payload = json.loads(received_data)
        event = payload['event']
        if event in events:
            logging.debug('Received %s with %s payload'%(event, payload))
            try:
                msg = events[event](payload['payload'])
                status = True
            except Exception as e:
                status = False
                msg = e.message
                logging.error(msg)
        else:
            status = False
            msg = 'No such event %s registered: payload - %s'%(
                event, palyload)
            logging.error(msg)
        to_send = json.dumps({'status': status, 'msg': msg})
        connection.send(to_send.encode('utf-8'))

def send_event(sockfile, event, payload=None):
    ''' Client needs to use this api to send events to the registered server '''
    if not os.path.exists(sockfile):
        raise Exception('Server not registered - %s'%sockfile)
    dct = {'event': event, 'payload': payload}
    actual_payload = json.dumps(dct)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sockfile)
    sock.sendall(actual_payload.encode('utf-8'))
    data = sock.recv(2048)
    sock.close()
    received_payload = json.loads(data.decode('utf-8'))
    if received_payload['status'] is not True:
        raise Exception(received_payload['msg'])
    return received_payload['msg']

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

class UdpServer(object):
    def __init__(self, server=None, port=None):
        self.server = server
        self.port = port
        self.create()

    def create(self):
        family, socktype, proto, canonname, sockaddr = \
            socket.getaddrinfo(self.server, self.port, 0,
                               socket.SOCK_DGRAM, 0, socket.AI_PASSIVE)[0]
        self.socket = socket.socket(family, socktype)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(sockaddr)

    def recv(self):
        request_data, address = self.socket.recvfrom(4096)
        return request_data, address

    def send(self, address, payload):
        try:
            self.socket.sendto(payload, address)
        except socket.error as e:
            if e.args[0] == errno.EAGAIN or e.args[0] == errno.EINTR:
                pass
            else:
                raise
