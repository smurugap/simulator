from lxml import etree
from spyne import Application, ServiceBase, \
    Integer, Unicode, AnyXml, ComplexModel, XmlData, XmlAttribute, rpc
import uuid
import models
import serializers
from collections import defaultdict
from common.util import Singleton, convert_template

class VM(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.dc_vms = defaultdict(list)
        self.vms = dict()

    def add_vm(self, dc_name, vm_name, dpgs, host, status='poweredOn'):
        self.dc_vms[dc_name].append(vm_name)
        self.vms[vm_name] = {'dpgs': dpgs,
                             'uuid': str(uuid.uuid4()),
                             'status': status,
                             'host': host}

    def list_vms_ex(self, dc_name, view_id, login_id):
        vms = self.dc_vms[dc_name]
        return convert_template('/root/simulator/vcenter/templates/list_vms_ex.xml.j2',
            login_id=login_id, view_id=view_id, vms=vms)

    def get_vm_network(self, vm_name):
        dpgs = self.vms[vm_name]['dpgs']
        return convert_template('/root/simulator/vcenter/templates/get_vm_network.xml.j2',
            dpgs=dpgs, vm=vm_name)

    def get_vm(self, vm_name):
        return convert_template('/root/simulator/vcenter/templates/get_vm.xml.j2', vm=vm_name)

    def get_vm_config(self, vm_name):
        dpg = self.vms[vm_name]['dpgs'][0]
        uuid = self.vms[vm_name]['uuid']
        return convert_template('/root/simulator/vcenter/templates/get_vm_config.xml.j2',
            vm=vm_name, uuid=uuid, dpg=dpg)

    def get_vm_runtime(self, vm_name):
        host = self.vms[vm_name]['host']
        status = self.vms[vm_name]['status']
        return convert_template('/root/simulator/vcenter/templates/get_vm_runtime.xml.j2',
            vm=vm_name, host=host, status=status)
