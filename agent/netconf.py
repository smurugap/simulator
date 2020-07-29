from common.exceptions import InvalidUsage
from agent.fabric import Fabric, CONFDIR
from common.ipc_api import send_event
from common.util import gevent
from flask import jsonify
import random
import os
import json
import ast

class Netconf(object):
    def get(self, fabric_name, devices=None, raw=None):
        pRouters = Fabric._get(fabric_name)[fabric_name]
        for device in devices or []:
            if device not in pRouters:
               raise InvalidUsage('device %s not found in fabric %s'%(
                                  device, fabric_name))
        devices = devices or list(pRouters.keys())
        payload = {'raw': True if raw else False}
        summary = dict()
        for device in devices:
            sock_file = Fabric.get_file(device, 'netconf', ftype='sock')
            output = send_event(sock_file, 'summary', payload)
            summary.update({device: output})
        return jsonify(summary)

    def post(self, fabric_name, devices=None, template=None, kv_pairs=None):
        pRouters = Fabric._get(fabric_name)[fabric_name]
        for device in devices or []:
            if device not in pRouters:
               raise InvalidUsage('device %s not found in fabric %s'%(
                                  device, fabric_name))
        devices = devices or list(pRouters.keys())
        if kv_pairs:
            payload_kv = dict()
            for kv_pair in kv_pairs:
                value = kv_pair['value']
                try:
                    value = ast.literal_eval(value)
                except ValueError:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                payload_kv[kv_pair['key']] = value
        if template:
            payload_register = {template['rpc_name']: template['content']}
        for device in devices:
            sock_file = Fabric.get_file(device, 'netconf', ftype='sock')
            if kv_pairs:
                send_event(sock_file, 'update', payload_kv)
            if template:
                send_event(sock_file, 'register', payload_register)
