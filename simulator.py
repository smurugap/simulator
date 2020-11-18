#!/usr/bin/python
import os
import copy
import gevent
import time
import hashlib
import subprocess
from ConfigParser import SafeConfigParser
#from gevent import monkey
#monkey.patch_all()
from engines.netconf import NetconfServer
from engines.openconfig import OpenConfig
from engines.snmp import SNMPServer
from engines.sflow import sFlowEngine
from engines.syslog import SyslogEngine
from common.docker_api import docker_h
from common.util import daemonize, watcher, get_file
import signal

config_file = get_file(docker_h.my_hostname, ftype='conf')

class Daemonize(object):
    def __init__(self, service, fn):
        self.pid_file = '/tmp/%s.pid'%(service)
        self.log_file = '/var/log/%s.log'%(service)
        self.fn = fn

    def stop(self):
        if not os.path.exists(self.pid_file):
            return
        with open(self.pid_file, 'r') as fd:
            pid = int(fd.read())
        os.kill(pid, 9)
        try:
            os.waitpid(pid, os.WNOHANG)
        except OSError:
            pass
        try:
            os.remove(self.pid_file)
        except OSError:
            pass

    def start(self):
        daemonize(self.pid_file, self.log_file, self.fn)

def parse_config():
    config = SafeConfigParser()
    config.read(config_file)
    return config

def get_md5sum(filename):
    with open(filename, 'r') as fd:
        content = fd.read()
    return hashlib.md5(content.encode()).hexdigest()

def get_service_config(config, service):
    service_config = dict(config.items("DEFAULTS"))
    service_config.update(dict(config.items(service)))
    return service_config

def get_peers(role, fabric, leafs, bleafs, spines, super_spines):
    peers = list()
    if role == 'leaf':
        start = super_spines
        peer_index = start + docker_h.my_index
        for index in range(spines):
            peers.append({'name': fabric+'-Spine'+str(index),
                          'index': peer_index,
                          'interface': 'et-0/0/%s'%peer_index})
    elif role == 'bleaf':
        if super_spines:
            prefix = '-SuperSpine'
            n_peers = super_spines
            start = spines
        else:
            prefix = '-Spine'
            n_peers = spines
            start = leafs
        peer_index = start + docker_h.my_index
        for index in range(n_peers):
            peers.append({'name': fabric+prefix+str(index),
                          'index': peer_index,
                          'interface': 'et-0/0/%s'%peer_index})
    elif role == 'super_spine':
        peer_index = docker_h.my_index
        for index in range(spines):
            peers.append({'name': fabric+'-Spine'+str(index),
                          'index': peer_index,
                          'interface': 'et-0/0/%s'%peer_index})
        for index in range(bleafs):
            peers.append({'name': fabric+'-BLeaf'+str(index),
                          'index': peer_index,
                          'interface': 'et-0/0/%s'%peer_index})
    elif role == 'spine':
        peer_index = docker_h.my_index
        for index in range(super_spines):
            peers.append({'name': fabric+'-SuperSpine'+str(index),
                          'index': peer_index,
                          'interface': 'et-0/0/%s'%peer_index})
        peer_index = docker_h.my_index
        for index in range(leafs):
            peers.append({'name': fabric+'-Leaf'+str(index),
                          'index': peer_index,
                          'interface': 'et-0/0/%s'%peer_index})
        if not super_spines:
            peer_index = peer_index + leafs
            for index in range(bleafs):
                peers.append({'name': fabric+'-BLeaf'+str(index),
                              'index': peer_index,
                              'interface': 'et-0/0/%s'%peer_index})
    return peers

class Services(object):
    def __init__(self):
        self.config = parse_config()
        self.md5sum = get_md5sum(config_file)

    def start_service(self, service):
        service_config = get_service_config(self.config, service)
        fabric = service_config['fabric']
        role = service_config['role']
        n_leafs = int(service_config['n_leafs'])
        n_spines = int(service_config['n_spines'])
        n_bleafs = int(service_config['n_bleafs'] or 0)
        n_super_spines = int(service_config['n_super_spines'] or 0)
        n_pifs = int(service_config['n_pifs'])
        version = service_config['version']
        model = service_config['model']
        socket = service_config.get('socket')
        peers = get_peers(role, fabric, n_leafs, n_bleafs,
                          n_spines, n_super_spines)
        if service == 'Netconf':
            username = service_config['username']
            password = service_config['password']
            secret = service_config['secret'] or None
            device_id = service_config['device_id'] or None
            manager = service_config['manager'] or None
            nc = NetconfServer(username=username, password=password,
                version=version, model=model, n_interfaces=n_pifs,
                peers=peers, socket=socket, manager=manager,
                secret=secret, device_id=device_id)
            self.nc = Daemonize('netconf', nc.start)
            self.nc.start()
        elif service == 'SNMP':
            oid_file = service_config.get('oids')
            server = service_config.get('collector')
            snmp = SNMPServer(n_interfaces=n_pifs, peers=peers,
                socket=socket, oid_file=oid_file, collector=server)
            self.snmp = Daemonize('snmp', snmp.start)
            self.snmp.start()
        elif service == 'sFlows':
            sflows_file = service_config.get('flows')
            server = service_config.get('collector')
            port = service_config.get('port', 6343)
            if server:
                sflow = sFlowEngine(server, sflows_file, port=port)
                self.sflow = Daemonize('sflow', sflow.start)
                self.sflow.start()
        elif service == 'Syslog':
            server = service_config.get('collector')
            port = service_config.get('port', 514)
            if server:
                syslog = SyslogEngine(server, port, socket=socket)
                self.syslog = Daemonize('syslog', syslog.start)
                self.syslog.start()
        elif service == "OpenConfig":
            port = service_config.get('port', 50051)
            program = "python engines/openconfig/main.py"
            self.openconfig = Daemonize('openconfig', None)
            subprocess.call("%s --socket %s --port %s --n_interfaces %d --pid %s &"%(
                program, socket, port, n_pifs, self.openconfig.pid_file), shell=True)

    def start(self):
        self.start_service("Netconf")
        self.start_service("SNMP")
        self.start_service("sFlows")
        self.start_service("Syslog")
        self.start_service("OpenConfig")
        notifier = watcher(config_file, self.monitor)

    def monitor(self, notifier):
        md5sum = get_md5sum(config_file)
        if md5sum != self.md5sum:
            self.md5sum = md5sum
            notifier.stop()
            self.stop()
            time.sleep(5)
            self.start()

    def stop(self):
        self.nc.stop()
        self.snmp.stop()
        if getattr(self, 'sflow', None):
            self.sflow.stop()
        if getattr(self, 'syslog', None):
            self.syslog.stop()
        self.openconfig.stop()

def main():
    services = Services()
    services.start()
    # Forward port 830 to port 22
    subprocess.call("socat TCP-LISTEN:830,fork TCP:127.0.0.1:22 &", shell=True)
    while True:
        gevent.sleep(60)

if __name__ == '__main__':
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    main()
