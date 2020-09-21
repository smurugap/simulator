from gevent import monkey
monkey.patch_all()
from common.docker_api import docker_h
from common.ipc_api import UdpClient
from common.constants import SAMPLES_PER_PKT
from common.util import watcher, touch
from scapy.all import IP, Ether, ICMP, raw, TCP, UDP
import argparse
import time
import sys
import json
import logging
import xdrlib

from engines.sflow import datagram

def encode(dct):
    """Decode a bytes object as an sFlow datagram"""
    packer = xdrlib.Packer()
    datagram.Datagram.encode(dct, packer)
    return packer

class sFlowEngine(object):
    def __init__(self, server, sflows_file, port=6343):
        self.server = UdpClient(server, port)
        self.sflows_file = sflows_file
        self.flows = list()
        touch(self.sflows_file)
        self.generate_sflow_headers()

    def callback(self, notifier):
        self.generate_sflow_headers()

    def read_sflows(self):
        with open(self.sflows_file, 'r') as fd:
            try:
                self.flows = json.load(fd)
            except Exception as e:
                print e
                pass

    def get_overlay_header(self, src_ip, dst_ip, proto=None,
                           sport=None, dport=None):
        eth = Ether(dst="aa:bb:cc:dd:ee:ff", src="00:11:22:33:44:55")
        ip = IP(dst=dst_ip, src=src_ip)
        if proto == 'TCP':
            proto = TCP(sport=sport, dport=dport)
        elif proto == 'UDP':
            proto = UDP(sport=sport, dport=dport)
        else:
            proto = ICMP()
        pkt = eth/ip/proto
        return raw(pkt)

    def generate_sflow_headers(self):
        self.read_sflows()
        self.samples = list()
        self.buffers = list()
        for flow in self.flows:
            pkt = self.get_overlay_header(flow['src_ip'], flow['dst_ip'],
                flow['proto'], int(flow.get('sport') or 0),
                int(flow.get('dport') or 0))
            self.samples.append({'flow_records': [{'header': pkt}],
                'input': int(flow['index']), 'source_id': int(flow['index'])})

        for i in range(0, len(self.samples), SAMPLES_PER_PKT):
            samples = self.samples[i:i+SAMPLES_PER_PKT]
            self.buffers.append(encode({'agent_address': docker_h.my_ip,
                'samples': samples}).get_buffer())

    def start(self):
        watcher(self.sflows_file, self.callback)
        while True:
            for buf in self.buffers:
                self.server.send(buf)
            time.sleep(1)

def parse_cli(args):
    '''Define and Parse arguments for the script'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', action='store', required=True,
                        help='Simulator name')
    parser.add_argument('--server', action='store', required=True,
                        help='sflow collector')
    parser.add_argument('--dport', action='store', default=6343,
                        type=int, help='List of dst ports')
    parser.add_argument('--flows', required=True, metavar="FILE",
                        help='JSON file with flows to sample')
    pargs = parser.parse_args(args)
    return pargs

if __name__ == '__main__':
    pargs = parse_cli(sys.argv[1:])
    generator = sFlowEngine(pargs.server, pargs.dport, pargs.flows, pargs.name)
    generator.create()
    daemon(generator.run, '/tmp/sflow-%s.pid'%pargs.name, '/tmp/sflow-%s.log'%pargs.name, True)
