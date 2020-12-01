from scripts.agent_api import SimulatorAgentApi
from collections import deque, defaultdict
import os
import json
import argparse
import sys

def update(content, template, kv_pairs, fabric, devices):
    agent_h = SimulatorAgentApi()
    payload = dict()
    if content:
        payload['template'] = {'content': content, 'rpc_name': os.path.basename(template)}
    if kv_pairs:
        kv_pair_payload = list()
        for kv_pair in kv_pairs:
            key, value = kv_pair.strip().split('=')
            kv_pair_payload.append({'key': key, 'value': value})
        payload['kv_pairs'] = kv_pair_payload
    if devices:
        payload['devices'] = devices
    agent_h.post('netconf/'+fabric, payload)

def parse_cli(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xml', metavar="FILE",
        help='location of the xml template file')
    parser.add_argument('--fabric', required=True,
        help='name of the fabric')
    parser.add_argument('--devices', nargs='+',
        help='Name of the devices')
    parser.add_argument('--kv-pairs', nargs='+',
        help='Any custom args to pass to function')
    pargs = parser.parse_args(args)
    return pargs

def main(template, kv_pairs, fabric, devices):
    content = None
    if template:
        with open(template, 'r') as fd:
            content = fd.read()
    update(content, template, kv_pairs, fabric, devices)

if __name__ == '__main__':
    pargs = parse_cli(sys.argv[1:])
    main(pargs.xml, pargs.kv_pairs, pargs.fabric, pargs.devices)
