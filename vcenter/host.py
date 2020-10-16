from lxml import etree
import uuid
import serializers
from collections import defaultdict
from common.util import convert_template, Singleton

class Host(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.dc_hosts = defaultdict(list)
        self.hosts = dict()

    def add_host(self, dc_name, host_name, neighbors):
        # neighbors = [{'5d9-qfx1': ['xe-0/0/0', 'xe-0/0/1']}, {'5d9-qfx2':  ['xe-0/0/0']}]
        self.hosts[host_name] = neighbors
        self.dc_hosts[dc_name].append(host_name)

    def update_hosts(self, propSet):
        propSet.val = list()
        propSet._setattribute('val', xsi_type='ArrayOfManagedObjectReference')
        for host_name, details in self.hosts.iteritems():
            mobj = serializers.ManagedObject()
            mobj.ManagedObjectReference = host_name
            mobj._setattribute('ManagedObjectReference', type='HostSystem')
            propSet.val.append(mobj)

    def update_host_managers(self, host_name, propSet):
        propSet._setattribute('val', xsi_type='HostConfigManager')
        obj = serializers.HostConfigManager()
        for elem in obj.__tag__.iterkeys():
            if elem == 'networkSystem':
                obj.networkSystem = 'hostnetworksystem-%s'%host_name
            else:
                setattr(obj, elem, elem+'-'+host_name)
        propSet.val = obj

    def set_param(self, parent, key, value, **kwargs):
        param = serializers.Parameter()
        param.parameter = serializers.ParameterInfo(key=key, value=value)
        param.parameter._setattribute('value', **kwargs)
        param.serialize(parent)

    def get_lldp_details(self, host_name):
        objs = list()
        nic_index = 0
        for neighbors in self.hosts[host_name]:
            for peer_name, nics in neighbors.items():
                for nic in nics:
                    obj = serializers.NetworkHint()
                    obj.device = 'vmnic%s'%nic_index
                    obj.lldpInfo.portId = nic
                    parent = obj.serialize()
                    lldp = parent.find('.//lldpInfo')
                    self.set_param(lldp, key='Aggregated Port ID', value=0, xsi_type='xsd:string')
                    self.set_param(lldp, key='Aggregation Status', value=1, xsi_type='xsd:string')
                    self.set_param(lldp, key='MTU', value=1514, xsi_type='xsd:string')
                    self.set_param(lldp, key='Port Description', value=nic, xsi_type='xsd:string')
                    self.set_param(lldp, key='System Name', value=peer_name, xsi_type='xsd:string')
                    nic_index = nic_index + 1
                    objs.append(parent)
        return objs

    def list_hosts(self, dc):
        hosts = list()
        hostnames = self.dc_hosts[dc]
        for hostname in hostnames:
           hosts.append(convert_template('/root/simulator/vcenter/templates/list_hosts.xml.j2',
                hostname=hostname, rtype='xml'))
        return hosts

    def list_hosts_ex(self, dc, view_id, login_id):
        hosts = self.dc_hosts[dc]
        return convert_template('/root/simulator/vcenter/templates/list_hosts_ex.xml.j2',
            login_id=login_id, view_id=view_id, hosts=hosts)

    def get_host(self, host):
        return convert_template('/root/simulator/vcenter/templates/get_host.xml.j2', hostname=host)
