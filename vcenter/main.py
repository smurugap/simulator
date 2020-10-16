import logging
logging.basicConfig(level=logging.DEBUG)

from lxml import etree
from spyne import Application, ServiceBase, \
    Integer, Unicode, AnyXml, ComplexModel, XmlData, XmlAttribute, rpc
from spyne import Iterable
from spyne.protocol.soap import Soap11
from spyne.protocol.xml import XmlDocument
from spyne.server.wsgi import WsgiApplication
from spyne.model.fault import Fault
from spyne.util.cherry import cherry_graft_and_start
import uuid
import models
import serializers
import server
import gevent
gevent.monkey.patch_all()

NS = 'urn:vim25'

class vCenterService(ServiceBase):
    @classmethod
    def call_wrapper(cls, ctx, args=None):
        ctx.udc = server.vCenter()
        return ServiceBase.call_wrapper(ctx, args)

    @rpc(AnyXml, _returns=AnyXml, _body_style='out_bare')
    def RetrieveServiceContent(ctx, _this):
        self = ctx.udc
        return self.get_service_content()

    @rpc(AnyXml, Unicode, Unicode, _returns=AnyXml, _body_style='out_bare')
    def Login(ctx, _this, userName, password):
        self = ctx.udc
        if (userName == 'root' and password == 'Embe1mpls') or \
           (userName == 'u' and password == 'p') or \
           (userName == 'user' and password == 'pass'):
            self.auth = serializers.AuthResponse()
            self.auth.key = self.login_id
            return self.auth.serialize()
        raise Fault('Client.Authentication', 'Authorization failed')

    @rpc(_body_style='out_bare')
    def Logout(ctx):
        return

    @rpc(models.CreateContainerViewModel, _returns=AnyXml, _body_style='bare')
    def CreateContainerView(ctx, req):
        self = ctx.udc
        view_id = str(uuid.uuid4())
        container = req.container.value
        self.views[view_id] = {'type': req.type, 'container': container}
        parent = etree.Element("returnval", type='ContainerView')
        parent.text = "session[%s]%s"%(self.login_id, view_id)
        return parent

    @rpc(_body_style='out_bare')
    def DestroyView(ctx):
        return

    @rpc(models.CreateFilterModel, _returns=AnyXml, _body_style='bare')
    def CreateFilter(ctx, req):
        self = ctx.udc
        filter_id = str(uuid.uuid4())
        obj_requested = req.spec.objectSet.obj.value
        self.filters[filter_id] = {'type': req.spec.propSet.type,
                                   'path': req.spec.propSet.pathSet,
                                   'obj': obj_requested}
        parent = etree.Element("returnval", type='PropertyFilter')
        parent.text = "session[%s]%s"%(self.login_id, filter_id)
        return parent

    @rpc(models.RetrievePropertiesModel, _returns=AnyXml, _body_style='bare')
    def RetrievePropertiesEx(ctx, req):
        self = ctx.udc
        prop_type = req.specSet.propSet.type
        prop_path = req.specSet.propSet.pathSet
        obj_type = req.specSet.objectSet.obj.type
        obj_requested = req.specSet.objectSet.obj.value
        response = serializers.RetrievePropertiesEx()
        response.objects.obj = obj_requested
        response.objects._setattribute('obj', type=obj_type)
        response.objects.propSet.name = prop_path
        if prop_type == 'ContainerView' and prop_path == 'view':
            view_id = obj_requested.split(']')[1]
            if self.views[view_id]['type'] == 'Datacenter':
                return self.dc.list_dc_ex(view_id, self.login_id)
            elif self.views[view_id]['type'] == 'HostSystem':
                dc = self.views[view_id]['container']
                return self.host.list_hosts_ex(dc, view_id, self.login_id)
            elif self.views[view_id]['type'] == 'DistributedVirtualPortgroup':
                dc = self.views[view_id]['container']
                return self.dpg.list_dpgs_ex(dc, view_id, self.login_id)
            elif self.views[view_id]['type'] == 'VirtualMachine':
                dc = self.views[view_id]['container']
                return self.vm.list_vms_ex(dc, view_id, self.login_id)
        if prop_type == 'Datacenter' and prop_path == 'name':
            return self.dc.get_dc(obj_requested)
        elif prop_type == 'HostSystem' and prop_path == 'name':
            return self.host.get_host(obj_requested)
        elif prop_type == 'HostSystem' and prop_path == 'configManager':
            self.host.update_host_managers(obj_requested, response.objects.propSet)
            return response.serialize()
        elif prop_type == 'DistributedVirtualPortgroup' and prop_path == 'config':
            return self.dpg.get_dpg_config(obj_requested)
        elif prop_type == 'DistributedVirtualPortgroup' and prop_path == 'name':
            return self.dpg.get_dpg(obj_requested)
        elif prop_type == 'ServiceInstance' and prop_path == 'content':
            return self.get_service_instance()
        elif prop_type == 'VirtualMachine' and prop_path == 'network':
            return self.vm.get_vm_network(obj_requested)
        elif prop_type == 'VirtualMachine' and prop_path == 'name':
            return self.vm.get_vm(obj_requested)
        elif prop_type == 'VirtualMachine' and prop_path == 'config':
            return self.vm.get_vm_config(obj_requested)
        elif prop_type == 'VirtualMachine' and prop_path == 'runtime':
            return self.vm.get_vm_config(obj_requested)

    @rpc(models.RetrievePropertiesModel, _returns=Iterable(models.CustomList), _body_style='bare')
    def RetrieveProperties(ctx, req):
        self = ctx.udc
        prop_type = req.specSet.propSet.type
        prop_path = req.specSet.objectSet.selectSet.path
        obj = req.specSet.objectSet.obj.value
        if prop_type == 'Datacenter' and prop_path == 'view':
            for dc in self.dc.list_dc():
                yield dc
        elif prop_type == 'HostSystem' and prop_path == 'view':
            view_id = obj.split(']')[1]
            dc = self.views[view_id]['container']
            for host in self.host.list_hosts(dc):
                yield host
#        elif prop_type == 'ContainerView' and prop_path == 'view':
#            self.update_hosts(response.objects.propSet)
#        elif prop_type == 'HostSystem' and prop_path == 'configManager':
#            self.update_host_managers(obj_requested, response.objects.propSet)
#        return response.serialize()

    @rpc(models.TypeVal, _returns=Iterable(models.CustomList), _body_style='bare')
    def QueryNetworkHint(ctx, req):
        self = ctx.udc
        host_name = ctx.in_document.find('.//{%s}_this'%NS).text.split('hostnetworksystem-')[1]
        for elem in self.host.get_lldp_details(host_name):
            yield elem

    @rpc(models.CreateCollectorForEvents, _returns=AnyXml, _body_style='bare')
    def CreateCollectorForEvents(ctx, req):
        self = ctx.udc
        dc = req.filter.entity.entity.value
        cid = str(uuid.uuid4())
        self.collectors[cid] = dc
        parent = etree.Element("returnval", type='EventHistoryCollector')
        parent.text = "session[%s]%s"%(self.login_id, cid)
        return parent

    @rpc(_body_style='out_bare')
    def SetCollectorPageSize(ctx):
        return

    @rpc(models.WaitForUpdatesEx, _body_style='bare')
    def WaitForUpdatesEx(ctx, req):
        self = ctx.udc
        gevent.sleep(20)
        return

application = Application(
    [vCenterService],
    tns=NS,
    in_protocol=Soap11(),
#    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    wsgi_app = WsgiApplication(application)
    cherry_graft_and_start(wsgi_app, port=443, ssl_module='pyopenssl', cert='/root/simulator/vcenter/ssl/certs/server.pem', key='/root/simulator/vcenter/ssl/private/server-privkey.pem', cacert='/root/simulator/vcenter/ssl/certs/ca-cert.pem')
