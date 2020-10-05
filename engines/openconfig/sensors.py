from engines.openconfig.gen import telemetry_pb2
from jinja2 import Template, Environment, meta
from common.docker_api import docker_h
import os
import json
import time
import gevent

MYDIR = os.path.dirname(os.path.abspath(__file__))
IGNORE_KEYWORDS = ['range']

def get_key_value(key, value):
    typ = value.keys()[0]
    if typ == "str_value":
        return telemetry_pb2.KeyValue(key=key, str_value=value[typ])
    elif typ == "uint_value":
        return telemetry_pb2.KeyValue(key=key, uint_value=int(value[typ]))
    elif typ == "sint_value":
        return telemetry_pb2.KeyValue(key=key, sint_value=int(value[typ]))
    elif typ == "double_value":
        return telemetry_pb2.KeyValue(key=key, double_value=int(value[typ]))
    elif typ == "int_value":
        return telemetry_pb2.KeyValue(key=key, int_value=int(value[typ]))
    elif typ == "bool_value":
        return telemetry_pb2.KeyValue(key=key, bool_value=bool(value[typ]))
    elif typ == "bytes_value":
        return telemetry_pb2.KeyValue(key=key, bytes_value=value[typ])

def get_kv_pairs(template):
    jdumps = json.loads(template)
    output = list()
    for entry in jdumps:
        for sensor, kv_pairs in entry.items():
            data = list()
            for kv_pair in kv_pairs:
                key = kv_pair.keys()[0]
                data.append(get_key_value(key, kv_pair[key]))
            output.append((sensor, data))
    return output

def get_templates_abs_path(template):
    return os.path.join(MYDIR, 'templates', template)

class BaseSensor(object):
    def __init__(self, my_queue, interval, context, n_interfaces=10, **kwargs):
        self.interval = interval
        self.queue = my_queue
        self.context = context
        self.n_interfaces = n_interfaces
        self.hostname = docker_h.my_hostname

    def run(self):
        count = 0
        while True:
            if self.context.is_active() is False:
                raise Exception('context is not active')
            for path_kv_pairs in self.get_kv_pairs():
                path, kv_pairs = path_kv_pairs
                data = telemetry_pb2.OpenConfigData(
                    system_id=self.hostname,
                    component_id=1,
                    sequence_number=count,
                    timestamp=int(time.time()),
                    path=path,
                    kv=kv_pairs)
                self.queue.put_nowait(data)
                count = count + 1
            gevent.sleep(self.interval)

    def _convert_template(self, template):
        with open(template, 'r') as fd:
            content = fd.read()
        parsed_content = Environment().parse(content)
        attrs = meta.find_undeclared_variables(parsed_content)
        kwargs = dict()
        for attr in attrs:
            if attr in IGNORE_KEYWORDS:
                continue
            kwargs[attr] = getattr(self, attr)
        template = Template(content)
        rendered = template.render(**kwargs)
        return rendered

    def get_kv_pairs(self):
        template = get_templates_abs_path(self.TEMPLATE)
        jsonstr = self._convert_template(template)
        return get_kv_pairs(jsonstr)

class Interfaces(BaseSensor):
    SENSOR = "/interfaces/interface/state/"
    TEMPLATE = "interfaces.json.j2"
    def __init__(self, interfaces=None, *args, **kwargs):
        self.interfaces = interfaces
        super(Interfaces, self).__init__(*args, **kwargs)

class SubInterfaces(BaseSensor):
    SENSOR = "/interfaces/interface/subinterfaces/subinterface/state/"
    TEMPLATE = "subinterfaces.json.j2"
    def __init__(self, interfaces=None, sub_interfaces=None, *args, **kwargs):
        self.interfaces = interfaces
        self.sub_interfaces = sub_interfaces
        super(SubInterfaces, self).__init__(*args, **kwargs)

class Components(BaseSensor):
    SENSOR = "/components/"
    TEMPLATE = "components.json.j2"
    def __init__(self, components=None, *args, **kwargs):
        self.components = components
        super(Components, self).__init__(*args, **kwargs)

class BGP(BaseSensor):
    SENSOR = "/network-instances/network-instance/protocols/protocol/bgp/"
    TEMPLATE = "bgp_neighbors.json.j2"
    def __init__(self, bgp=None, *args, **kwargs):
        self.bgp = bgp
        super(BGP, self).__init__(*args, **kwargs)

class LLDP(BaseSensor):
    SENSOR = "/lldp/"
    TEMPLATE = "lldp.json.j2"
    def __init__(self, lldp=None, *args, **kwargs):
        self.lldp = lldp
        super(LLDP, self).__init__(*args, **kwargs)
