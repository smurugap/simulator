from common.exceptions import InvalidUsage
from agent.fabric import Fabric
from common.ipc_api import send_event

class SNMP(object):
    def post(self, fabric_name, devices=None, oids=None, trap=None):
        pRouters = Fabric._get(fabric_name)[fabric_name]
        for device in devices or []:
            if device not in pRouters:
               raise InvalidUsage('device %s not found in fabric %s'%(
                                  device, fabric_name))
        devices = devices or list(pRouters.keys())
        for device in devices:
            sock_file = Fabric.get_file(device, 'snmp', ftype='sock')
            if oids:
                send_event(sock_file, 'update', oids)
            if trap:
                send_event(sock_file, 'send_trap', trap)
