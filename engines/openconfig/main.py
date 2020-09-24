from engines.openconfig.gen import authentication_pb2
from engines.openconfig.gen import authentication_pb2_grpc
from engines.openconfig.gen import telemetry_pb2
from engines.openconfig.gen import telemetry_pb2_grpc
from collections import defaultdict
from common.docker_api import docker_h
from common.util import register_event, get_file
from common.ipc_api import register_listener
from gevent import queue
from sensors import Interfaces, SubInterfaces, Components
import gevent
import json
import grpc
from concurrent import futures
import argparse
import os
import sys

OPENCONFIG_EVENTS = dict()
PATHS = {'/interfaces/interface/state/': Interfaces,
         '/interfaces/interface/subinterfaces/subinterface/state/': SubInterfaces,
         '/components/': Components}

def merge_dicts(a, b):
    "http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge"
    "merges b into a"
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key])
            elif a[key] == b[key]:
                pass # same leaf value
            elif isinstance(a[key], list) and isinstance(b[key], list):
                for idx, val in enumerate(b[key]):
                    a[key][idx] = merge(a[key][idx], b[key][idx])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class Telemetry(telemetry_pb2_grpc.OpenConfigTelemetryServicer):
    def __init__(self, socket, n_interfaces=10, *args, **kwargs):
        super(Telemetry, self).__init__(*args, **kwargs)
        self.interfaces = defaultdict(dict)
        self.sub_interfaces = defaultdict(dict)
        self.components = defaultdict(dict)
        self.n_interfaces = n_interfaces
        self.socket = socket

    def update(self, sensor_kv_pairs):
        # self.interfaces['et-0/0/0']['admin-status'] = 'down'
        # {'interfaces': {'et-0/0/0': {'admin-status': 'down'}}}
        # {'components': {'Routing Engine0': {'cpu-utilization-idle': {'state/value': 23}}}}
        for sensor, kv_pairs in sensor_kv_pairs.items():
            dct = getattr(self, sensor)
            for k, v in kv_pairs.items():
                if type(dct[k]) is dict:
                    dct[k].update(v)
                else:
                    dct[k] = v

    def telemetrySubscribe(self, request, context):
        register_event('update', OPENCONFIG_EVENTS, self.update)
        register_listener(self.socket, OPENCONFIG_EVENTS)
        my_queue = queue.Queue()
        for path in request.path_list:
            if path.path not in PATHS:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid path")
            interval = path.sample_frequency/1000
            if path.path in PATHS:
                 obj = PATHS[path.path](my_queue=my_queue,
                     interval=interval, context=context,
                     n_interfaces=self.n_interfaces,
                     interfaces=self.interfaces,
                     sub_interfaces=self.sub_interfaces,
                     components=self.components)
                 gevent.spawn(obj.run)
        while True:
            try:
                if context.is_active() is False:
                    raise Exception('Channel is inactive')
                yield my_queue.get_nowait()
            except queue.Empty:
                gevent.sleep(1)

class Auth(authentication_pb2_grpc.LoginServicer):
    def LoginCheck(self, request, context):
        return authentication_pb2.LoginReply(result=True)

class OpenConfig(object):
    def __init__(self, port=32767, socket=None, n_interfaces=10):
        self.socket = socket
        self.n_interfaces = n_interfaces
        self.port = port

    def start(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        authentication_pb2_grpc.add_LoginServicer_to_server(Auth(), server)
        telemetry_pb2_grpc.add_OpenConfigTelemetryServicer_to_server(
            Telemetry(self.socket, self.n_interfaces), server)
        server.add_insecure_port('[::]:%s'%self.port)
        server.start()
        server.wait_for_termination()

def parse_cli(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', required=True, metavar="FILE",
        help='location of the unix domain socket file')
    parser.add_argument('--port', default=32767, type=int,
        help='Openconfig port to listen on')
    parser.add_argument('--n_interfaces', default=48, type=int,
        help='No of interfaces in the physical device')
    parser.add_argument('--pid', required=True, metavar="FILE",
        help='file to write the pid of the process')
    pargs = parser.parse_args(args)
    return pargs

if __name__ == '__main__':
    pargs = parse_cli(sys.argv[1:])
    with open(pargs.pid, 'w') as fd:
        fd.write(str(os.getpid()))
    OpenConfig(socket=pargs.socket, port=pargs.port,
               n_interfaces=pargs.n_interfaces).start()
