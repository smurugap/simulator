from agent.fabric import Fabric, CONFDIR
from collections import defaultdict
from common.util import get_random_cidr, get_random_ip, get_prouter_index
from common.constants import SFLOW_OVERLAY_IP_PROTOCOLS
import random
import os
import json

class sFlow(object):
    def update_flows(self, prouter):
        with open(os.path.join(CONFDIR, prouter+'.sflows'), 'w') as fd: 
            json.dump(self.flows[prouter], fd, indent=4)

    def post(self, fabric_name, action='start', n_flows=None,
             bms_per_router=None, direction='ingress'):
        self.leafs = list(); self.spines = list()
        self.flows = defaultdict(list)
        self.bms_per_prouter = int(bms_per_router or 0)
        pRouters = Fabric._get(fabric_name)[fabric_name]
        self.direction = direction
        for prouter, info in pRouters.items():
            if info['role'] == 'leaf':
                self.leafs.append(prouter)
            else:
                self.spines.append(prouter)
        if action.lower() == 'start':
            for i in range(n_flows):
                self.add_sflow()
        for prouter in self.leafs + self.spines:
            self.update_flows(prouter)

    def add_sflow(self):
        cidr = get_random_cidr()
        src_ip = get_random_ip(cidr)
        dst_ip = get_random_ip(cidr)
        leafs = random.sample(self.leafs, 2)
        spine = random.choice(self.spines)
        sport = random.randint(30000, 65535)
        dport = random.randint(10, 2000)
        src_leaf = leafs[0]
        dst_leaf = leafs[1]

        if self.direction == 'ingress':
            src_leaf_index = len(self.spines) + \
                random.randint(0, self.bms_per_prouter-1)
            spine_index = get_prouter_index(src_leaf)
            dst_leaf_index = get_prouter_index(spine)
        elif self.direction == 'egress':
            src_leaf_index = get_prouter_index(spine)
            spine_index = get_prouter_index(dst_leaf)
            dst_leaf_index = len(self.spines) + \
                random.randint(0, self.bms_per_prouter-1)

        proto = random.choice(SFLOW_OVERLAY_IP_PROTOCOLS)
        self.flows[src_leaf].append({'src_ip': src_ip, 'dst_ip': dst_ip,
             'proto': proto, 'sport': sport, 'dport': dport,
             'index': src_leaf_index})
        self.flows[dst_leaf].append({'src_ip': src_ip, 'dst_ip': dst_ip,
             'proto': proto, 'sport': sport, 'dport': dport,
             'index': dst_leaf_index})
        self.flows[spine].append({'src_ip': src_ip, 'dst_ip': dst_ip,
             'proto': proto, 'sport': sport, 'dport': dport,
             'index': spine_index})
