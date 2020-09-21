from common.exceptions import InvalidUsage
from agent.fabric import Fabric
from common.ipc_api import send_event
from common.util import gevent
from flask import jsonify
import random
import os
import json
import ast

class OpenConfig(object):
    def post(self, fabric_name, kv_pairs):
        '''
        {
        "test-Leaf0": {"interfaces": {"et-0/0/1": {"admin-status": "DOWN",
                                                   "oper-status": "DOWN"},
                                      "et-0/0/2": {"oper-status": "DOWN"}
                                     }
                      },
        "test-Leaf1": {"interfaces": {"et-0/0/3": {"oper-status": "DOWN"}},
                       "sub_interfaces": {"et-0/0/4.10": {"in-pkts": 10000000}}
                      }
        }
        '''
        pRouters = Fabric._get(fabric_name)[fabric_name]
        devices = kv_pairs.keys()
        for device in devices:
            if device not in pRouters:
               raise InvalidUsage('device %s not found in fabric %s'%(
                                  device, fabric_name))
        for device, sensors_info in kv_pairs.items():
            sock_file = Fabric.get_file(device, 'openconfig', ftype='sock')
            try:
                sensors_info = ast.literal_eval(sensors_info)
            except:
                pass
            send_event(sock_file, 'update', sensors_info)
