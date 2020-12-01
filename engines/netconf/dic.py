import os
import sys
import time
import select
import argparse
import socket
import errno
from common.util import get_sha1

KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC/qMKn98s//RlFXs24idBnvKPuzZEphCHcX7H2LURltLWyWn7yUN/ylpS3wtcn0OAnE07uBasZUP4ViBynNzKx0n+JYyDLtbG0W4alknodGxl4y3kxYCuyTrHAkShiTBQIkMPZRzxskO0F2kopoSAE8TT8l40Az2ZDX08B4umMyEg4RSzI2enIaaNBKaowV5Pu7PqelTCpJd7HCfniEbPeYbv/3nqT40pWtDuu/5OCHoST4PeHgHnyO9kk/DLs778ikxyA+OmUUcKNppETFiCoZ8+GQHsoa54F+igT8lJ65exuNzbkgp7Sv6KTOrme9orJgs2co9C+N2XmTmIPc9wh"

class TcpClient(object):
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.create()

    def create(self):
        family, socktype, proto, canonname, sockaddr = \
            socket.getaddrinfo(self.server, self.port, 0,
                               socket.SOCK_STREAM, 0, 0)[0]
        self.socket = socket.socket(family, socktype)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.connect(sockaddr)

    def send(self, message):
        while True:
            try:
                self.socket.send(message)
                return
            except socket.error as e:
                if e.args[0] == errno.EAGAIN or e.args[0] == errno.EINTR:
                    pass
                else:
                    raise

    def close(self):
        self.socket.close()

class DeviceInitiatedConnection(object):
    def __init__(self, jfm_addr, nc_addr, device_id, secret):
        self.jfm_server, self.jfm_port = jfm_addr
        self.nc_server, self.nc_port = nc_addr
        self.device_id = device_id
        self.secret = secret
        self.payload = self.get_initial_payload()
        self.jfm_socket = None
        self.nc_socket = None

    def get_initial_payload(self):
        sha1 = get_sha1(self.secret, KEY)
        payload = "MSG-ID: DEVICE-CONN-INFO\r\n"
        payload = payload + "MSG-VER: V1\r\n"
        payload = payload + "DEVICE-ID: " + self.device_id + "\r\n"
        payload = payload + "HOST-KEY: " + KEY + "\r\n"
        payload = payload + "HMAC: " + sha1 + "\r\n\r\n\r\n"
        return payload

    def start(self):
        self.jfm_socket = TcpClient(self.jfm_server, self.jfm_port)
        self.jfm_socket.send(self.payload)
        self.nc_socket = TcpClient(self.nc_server, self.nc_port)

    def bridge(self):
        inputs = [self.jfm_socket.socket, self.nc_socket.socket]
        outputs = []
        while True:
            try:
                readable, writable, exceptional = select.select(inputs, outputs, inputs)
            except select.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK or err == errno.EINTR:
                    continue
                raise
            for s in readable:
                data = s.recv(65535)
                if not data:
                    self.jfm_socket.close()
                    self.nc_socket.close()
                else:
                    if s == self.jfm_socket.socket:
                        self.nc_socket.send(data)
                    else:
                        self.jfm_socket.send(data)

    def close(self):
        if self.jfm_socket:
            self.jfm_socket.close()
        if self.nc_socket:
            self.nc_socket.close()

    def run(self):
        time.sleep(15)
        while True:
            try:
                self.start()
                self.bridge()
            except Exception as e:
                self.close()
                time.sleep(5)

def main(manager, prouter, device_id, secret):
    dic = DeviceInitiatedConnection((manager, 7804), (prouter, 22),
        device_id, secret)
    dic.run()

def parse_cli(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manager', required=True,
        help='Address of the controller')
    parser.add_argument('--router', default="127.0.0.1",
        help='Address of the Router')
    parser.add_argument('--device_id', required=True,
        help='Device Id mapping in the controller')
    parser.add_argument('--secret', required=True,
        help='Secret authorizing the device')
    pargs = parser.parse_args(args)
    return pargs

if __name__ == '__main__':
    pargs = parse_cli(sys.argv[1:])
    main(pargs.manager, pargs.router, pargs.device_id, pargs.secret)
