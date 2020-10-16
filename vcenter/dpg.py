from lxml import etree
from spyne import Application, ServiceBase, \
    Integer, Unicode, AnyXml, ComplexModel, XmlData, XmlAttribute, rpc
import uuid
import models
import serializers
from collections import defaultdict
from common.util import Singleton, convert_template

class DPG(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.dc_dpgs = defaultdict(list)
        self.dpgs = dict()

    def add_dpg(self, dc_name, dpg_name, dvs_name, vlan_id):
        self.dc_dpgs[dc_name].append(dpg_name)
        self.dpgs[dpg_name] = {'vlan_id': vlan_id, 'dvs': dvs_name}

    def list_dpgs_ex(self, dc_name, view_id, login_id):
        dpgs = self.dc_dpgs[dc_name]
        return convert_template('/root/simulator/vcenter/templates/list_dpgs_ex.xml.j2',
            login_id=login_id, view_id=view_id, dpgs=dpgs)

    def get_dpg_config(self, dpg_name):
        dvs = self.dpgs[dpg_name]['dvs']
        vlan_id = self.dpgs[dpg_name]['vlan_id']
        return convert_template('/root/simulator/vcenter/templates/get_dpg_config_ex.xml.j2',
            dpg=dpg_name, dvs=dvs, vlan_id=vlan_id)

    def get_dpg(self, dpg_name):
        return convert_template('/root/simulator/vcenter/templates/get_dpg_ex.xml.j2',
            dpg=dpg_name)
