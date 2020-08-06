from common.exceptions import InvalidUsage
from common.ipc_api import send_event
from logging.handlers import SysLogHandler
from agent.fabric import Fabric

class Syslog(object):
    def post(self, fabric_name, devices=None, level=None, facility=None, message=None):
        if facility not in SysLogHandler.facility_names:
            raise InvalidUsage('Valid facility names are %s'%(
                list(SysLogHandler.facility_names.keys())))
        if level not in SysLogHandler.priority_names:
            raise InvalidUsage('Valid levels are %s'%(
                list(SysLogHandler.priority_names.keys())))
        pRouters = Fabric._get(fabric_name)[fabric_name]
        for device in devices or []:
            if device not in pRouters:
               raise InvalidUsage('device %s not found in fabric %s'%(
                                  device, fabric_name))
        devices = devices or list(pRouters.keys())
        payload = {'facility': facility, 'message': message, 'level': level}
        for device in devices:
            sock_file = Fabric.get_file(device, 'syslog', ftype='sock')
            send_event(sock_file, 'send_syslog', payload)
