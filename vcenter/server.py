from lxml import etree
from spyne import Application, ServiceBase, \
    Integer, Unicode, AnyXml, ComplexModel, XmlData, XmlAttribute, rpc
import uuid
import models
import serializers
from vcenter.dc import DataCenter
from vcenter.host import Host
from vcenter.dpg import DPG
from vcenter.vm import VM
from common.util import Singleton, convert_template

class vCenter(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.dc = DataCenter()
        self.host = Host()
        self.dpg = DPG()
        self.vm = VM()
        self.login_id = str(uuid.uuid4())
        self.views = dict()
        self.filters = dict()
        self.collectors = dict()
        self.test()

    def test(self):
        self.dc.add_dc('DC0')
        self.dc.add_dc('DC1')
        self.host.add_host('DC0', 'host1', [{'5d9-qfx1': ['xe-0/0/0']}, {'5d9-qfx2':  ['xe-0/0/0']}])
        self.host.add_host('DC0', 'host2', [{'5d9-qfx1': ['xe-0/0/1']}, {'5d9-qfx3':  ['xe-0/0/0']}])
        self.host.add_host('DC1', 'host3', [{'6d9-qfx1': ['xe-0/0/0']}, {'6d9-qfx2':  ['xe-0/0/0']}])
        self.host.add_host('DC1', 'host4', [{'6d9-qfx1': ['xe-0/0/1']}, {'6d9-qfx3':  ['xe-0/0/0']}])
        self.dpg.add_dpg('DC0', 'dpg0', 'dvs0', 10)
        self.dpg.add_dpg('DC0', 'dpg1', 'dvs0', 11)
        self.dpg.add_dpg('DC0', 'dpg2', 'dvs1', 12)
        self.dpg.add_dpg('DC1', 'dpg3', 'dvs2', 10)
        self.vm.add_vm('DC0', 'vm0', ['dpg0', 'dpg1'], 'host1')
        self.vm.add_vm('DC0', 'vm1', ['dpg0'], 'host2')
        self.vm.add_vm('DC0', 'vm2', ['dpg1'], 'host2')
        self.vm.add_vm('DC1', 'vm3', ['dpg3'], 'host3')

    def get_service_content(self):
        return convert_template('/root/simulator/vcenter/templates/service_content.xml.j2', rtype='xml')

    def get_service_instance(self):
        return convert_template('/root/simulator/vcenter/templates/service_instance.xml.j2', rtype='xml')
