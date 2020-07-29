#!/usr/bin/python
import copy
import gevent
import time
from gevent import monkey
monkey.patch_all()
from engines.NetConf import NetconfServer
from engines.snmp import SNMPServer
from engines.sflow import sFlowEngine
from ConfigParser import SafeConfigParser
from common.docker_api import docker_h

conf_file = '/etc/simulator/'+docker_h.my_hostname+'.conf'

def parse_config(config_file):
    config = SafeConfigParser()
    config.read(config_file)
    return config

def get_service_config(config, service):
    service_config = dict(config.items("DEFAULTS"))
    service_config.update(dict(config.items(service)))
    return service_config

def start_service(config, service):
    service_config = get_service_config(config, service)
    if service_config['role'] == 'leaf':
       peer_prefix = service_config['fabric']+'-Spine'
    elif service_config['role'] == 'spine':
       peer_prefix = service_config['fabric']+'-Leaf'
    elif service_config['role'] == 'bleaf':
       peer_prefix = service_config['fabric']+'-Spine'

    n_peers = int(service_config['n_peers'])
    n_pifs = int(service_config['n_pifs'])
    version = service_config['version']
    model = service_config['model']
    socket = service_config.get('socket')
    if service == 'Netconf':
        nc = NetconfServer()
        gevent.spawn(nc.start, version=version, n_peers=n_peers,
                     n_interfaces=n_pifs, peer_prefix=peer_prefix,
                     model=model, socket=socket)
    elif service == 'SNMP':
        oid_file = service_config.get('oids')
        n_bleafs = int(service_config.get('n_bleafs') or 0)
        snmp = SNMPServer(peer_prefix=peer_prefix, n_peers=n_peers,
                          n_interfaces=n_pifs, socket=socket, oid_file=oid_file)
        gevent.spawn(snmp.start)
    elif service == 'sFlows':
        sflows_file = service_config.get('flows')
        server = service_config.get('collector')
        if server:
            sflow = sFlowEngine(server, sflows_file)
            gevent.spawn(sflow.start)

def main(config):
    start_service(config, "Netconf")
    start_service(config, "SNMP")
    start_service(config, "sFlows")
    while True:
        time.sleep(60)

if __name__ == '__main__':
    config = parse_config(conf_file)
    main(config)
