import uuid
from vcenter import serializers
from vcenter.host import Host
from common.util import Singleton, convert_template

class DataCenter(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.datacenters = set()

    def add_dc(self, name):
        self.datacenters.add(name)

    def delete_dc(self, name):
        self.datacenters.remove(name)

    def list_dc_ex(self, view_id, login_id):
        return convert_template('/root/simulator/vcenter/templates/list_dc_ex.xml.j2',
            rtype='xml', view_id=view_id, datacenters=list(self.datacenters), login_id=login_id)

    def list_dc(self):
        dcs = list()
        for dc in self.datacenters:
            dcs.append(convert_template('/root/simulator/vcenter/templates/list_dc.xml.j2',
            rtype='xml', dc=dc))
        return dcs

    def get_dc(self, dc):
        return convert_template('/root/simulator/vcenter/templates/get_dc.xml.j2',
            rtype='xml', dc=dc)
