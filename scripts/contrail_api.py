from common.constants import USERNAME, PASSWORD, VALID_OVERLAY_ROLES
from vnc_api.vnc_api import *
from common.rest_api import RestServer
from common.util import get_random_cidr, elem2dict, time_taken, retry, get_an_ip
from lxml import etree
from netaddr import IPNetwork, IPAddress
import uuid
import random

NODE_PROFILES = ['juniper-mx', 'juniper-qfx10k', 'juniper-qfx10k-lean',
                 'juniper-qfx5k', 'juniper-qfx5k-lean', 'juniper-srx']

class ConfigApi(object):
    def __init__ (self, username, password, project_name='admin',
                  domain_name='Default', auth_host=None,
                  contrail_args=None):
        config = contrail_args['config']
        analytics = contrail_args.get('analytics') or config
        server = config['servers'][0]
        auth_host = auth_host or server
        config_api = config['servers']
        api_ssl = config.get('ssl', False)
        self.analytics_api = analytics.get('server', server)
        self.analytics_ssl = analytics.get('ssl', api_ssl)
        self.csn = contrail_args.get('csn', {}).get('servers', [])
        self.domain_name = 'default-domain' \
            if domain_name == 'Default' else domain_name
        self.project_name = project_name
        self.vnc = VncApi(username=username,
                          password=password,
                          tenant_name=project_name,
                          domain_name=domain_name,
                          api_server_host=config_api,
                          api_server_use_ssl=api_ssl,
                          auth_host=auth_host)
        self.vns = dict()
        self.vn_objs = dict()
        self.lr_objs = dict()
        self.sg_objs = dict()
        self.pp_objs = dict()

    @property
    def analytics(self):
        if not getattr(self, '_analytics', None):
            aaa_mode = self.vnc.get_aaa_mode()
            self._analytics = AnalyticsApi(self.analytics_api,
                                           token=self.vnc._auth_token,
                                           use_ssl=self.analytics_ssl)
        return self._analytics

    @retry(delay=30, tries=60)
    def wait_for_job_to_finish(self, job_name, execution_id):
        table = 'ObjectJobExecutionTable'
        query = [[{'name': 'Messagetype', 'value': 'JobLog', 'op': 1}]]
        response = self.analytics.post_query(table, where_clause=query,
            select_fields=['MessageTS', 'Messagetype', 'ObjectLog'])
        for resp in response or []:
            dct = elem2dict(etree.fromstring(resp['ObjectLog']))
            log = dct['log_entry']['JobLogEntry']
            if log['name'] == job_name and \
                log['execution_id'] == execution_id:
                if log['status'].upper() == 'SUCCESS':
                    print 'job %s with exec id %s finished'%(job_name, execution_id)
                    return True
                elif log['status'].upper() == 'FAILURE':
                    assert False, 'job %s with exec id %s failed'%(job_name, execution_id)
        else:
            print 'job %s with exec id %s hasnt completed'%(job_name, execution_id)
        return False

    def get_fq_name(self, name):
        return [self.domain_name, self.project_name, name]

    def get_network(self, name):
        if name not in self.vns:
            vlan = None; cidr=None
            fq_name = self.get_fq_name(name)
            vn_obj = self.vnc.virtual_network_read(fq_name=fq_name)
            annotations = vn_obj.get_annotations() or KeyValuePairs()
            for kvp in annotations.get_key_value_pair():
                if kvp.key.lower() == 'test:vlan':
                    vlan = int(kvp.value)
                    break
            sn = vn_obj.get_network_ipam_refs()[0]['attr'].ipam_subnets[0]
            cidr = "/".join([sn.subnet.ip_prefix, str(sn.subnet.ip_prefix_len)])
            self.vns[name] = {'name': name, 'cidr': cidr, 'vlan': vlan}
            self.vn_objs[name] = vn_obj
        return self.vns[name]

    def get_network_obj(self, name):
        if name not in self.vn_objs:
            self.get_network(name)
        return self.vn_objs[name]

    @time_taken
    def create_network(self, name, cidr, vlan, routed=False, **kwargs):
        fq_name = self.get_fq_name(name)
        subnet, mask = cidr.split('/')
        vn_obj = VirtualNetwork(name, parent_type='project',
                                fq_name=fq_name)
        vn_obj.add_network_ipam(NetworkIpam(),
                                VnSubnetsType([IpamSubnetType(
                                subnet=SubnetType(subnet, mask))]))
        if routed is True:
            vn_obj.set_virtual_network_category('routed')
        kv_pairs = KeyValuePairs()
        kv_pairs.add_key_value_pair(KeyValuePair(key='test:vlan',
                                    value=str(vlan)))
        vn_obj.set_annotations(kv_pairs)
        try:
            self.vnc.virtual_network_create(vn_obj)
            self.vns[name] = {'name': name, 'cidr': cidr, 'vlan': vlan}
            self.vn_objs[name] = vn_obj
            print 'Created VN', fq_name[-1]
        except RefsExistError:
            pass
        return self.get_network(name)

    def delete_network(self, name, **kwargs):
        fq_name = self.get_fq_name(name)
        try:
            self.vnc.virtual_network_delete(fq_name=fq_name)
            print 'Deleted VN', fq_name[-1]
        except NoIdError:
            pass
        self.vns.pop(name, None)
        self.vn_objs.pop(name, None)

    def get_vpg_fqname(self, fabric_name, name):
        return ['default-global-system-config', fabric_name, name]

    @time_taken
    def create_workload(self, name, pifs, networks, fabric_name, **kwargs):
        fq_name = self.get_vpg_fqname(fabric_name, name)
        obj = VirtualPortGroup(name, fq_name=fq_name,
                               parent_type='fabric')
        try:
            uuid = self.vnc.virtual_port_group_create(obj)
        except RefsExistError:
            obj = self.vnc.virtual_port_group_read(fq_name=fq_name)
        obj.set_physical_interface_list([])
        for pif in pifs:
            pif_fqname = ['default-global-system-config']+pif.split(':')
            pif_obj = self.vnc.physical_interface_read(fq_name=pif_fqname)
            obj.add_physical_interface(pif_obj)
        self.vnc.virtual_port_group_update(obj)
        for index, network in enumerate(networks):
            port_name = name+'-port'+str(index)
            self.create_port(port_name, network, vpg=fq_name, pifs=pifs)
        print 'Created VPG', fq_name[-1]

    @time_taken
    def delete_workload(self, name, fabric_name, **kwargs):
        fq_name = self.get_vpg_fqname(fabric_name, name)
        try:
            vpg_obj = self.vnc.virtual_port_group_read(fq_name=fq_name)
        except NoIdError:
            return
        for vmi in vpg_obj.get_virtual_machine_interface_refs() or []:
            self.delete_port(id=vmi['uuid'])
        self.vnc.virtual_port_group_delete(fq_name=fq_name)
        print 'Deleted VPG', fq_name[-1]

    @time_taken
    def create_port(self, name, vn, vpg=None, pifs=None, device_owner=None):
        fq_name = self.get_fq_name(name)
        vn_obj = self.get_network_obj(vn)
        port_obj = VirtualMachineInterface(name,
            fq_name=fq_name, parent_type='project')
        port_obj.add_virtual_network(vn_obj)
        if vpg:
            device_owner = 'baremetal:None'
            interfaces = list()
            for pif in pifs:
                prouter, port = pif.split(':')
                interfaces.append({'switch_info': prouter,
                                   'port_id': port, 'fabric': vpg[1]})
            ll_info = {'local_link_information': interfaces}
            vlan = self.vns[vn].get('vlan')
            vmi_props = VirtualMachineInterfacePropertiesType()
            vmi_props.set_sub_interface_vlan_tag(int(vlan))
            port_obj.set_virtual_machine_interface_properties(vmi_props)
            kv_pairs = KeyValuePairs()
            vnic_kv = KeyValuePair(key='vnic_type', value='baremetal')
            kv_pairs.add_key_value_pair(vnic_kv)
            vpg_kv = KeyValuePair(key='vpg', value=vpg[-1])
            kv_pairs.add_key_value_pair(vpg_kv)
            bind_kv = KeyValuePair(key='profile', value=json.dumps(ll_info))
            kv_pairs.add_key_value_pair(bind_kv)
            port_obj.set_virtual_machine_interface_bindings(kv_pairs)
        if device_owner:
            port_obj.set_virtual_machine_interface_device_owner(device_owner)
        try:
            self.vnc.virtual_machine_interface_create(port_obj)
        except RefsExistError:
            return self.read_port(fq_name=fq_name)
#        iip_obj = InstanceIp(name=fq_name[-1])
#        iip_obj.add_virtual_network(vn_obj)
#        iip_obj.add_virtual_machine_interface(port_obj)
#        self.vnc.instance_ip_create(iip_obj)
        print 'Created VMI', name
        return port_obj

    def delete_port(self, **kwargs):
#        try:
#            self.vnc.instance_ip_delete(fq_name=fq_name[-1:])
#        except NoIdError:
#            pass
        try:
            self.vnc.virtual_machine_interface_delete(**kwargs)
            print 'Deleted VMI', kwargs
        except NoIdError:
            pass

    def read_port(self, **kwargs):
        return self.vnc.virtual_machine_interface_read(**kwargs)

    @time_taken
    def create_firewall_filter(self, name, fabric_name, workloads, rules=None):
        ''' Create Security group using VNC api '''
        ''' each rule can have src_ip, dst_ip, protocol, src_port, dst_port '''
        def _get_rule(dst_addr, protocol, dst_port):
            dst_addr = AddressType(subnet=SubnetType(dst_addr, 32))
            src_addr = AddressType(security_group='local')
            rule = PolicyRuleType(rule_uuid=str(uuid.uuid4()), direction='>',
                                  protocol=protocol, src_addresses=[src_addr],
                                  src_ports=[PortType(0, 65535)],
                                  dst_addresses=[dst_addr],
                                  dst_ports=[PortType(dst_port, dst_port),
                                             PortType(22, 22)],
                                  ethertype='IPv4')
            return rule
        fq_name = self.get_fq_name(name)
        crules = [_get_rule(rule['dst_ip'], rule['protocol'].lower(),
                            rule['dst_port']) for rule in rules]
        sg_obj = SecurityGroup(name, parent_type='project', fq_name=fq_name,
                               security_group_entries=PolicyEntriesType(crules))
        try:
            self.vnc.security_group_create(sg_obj)
            self.sg_objs[name] = sg_obj
            print 'Created SG', fq_name[-1]
        except RefsExistError:
            self.sg_objs[name] = self.vnc.security_group_read(fq_name=fq_name)
            pass
        for workload in workloads:
            vpg_fq_name = self.get_vpg_fqname(fabric_name, workload)
            self.assoc_security_group_to_vpg(name, vpg_fq_name)

    @time_taken
    def delete_firewall_filter(self, name):
        fq_name = self.get_fq_name(name)
        try:
            obj = self.vnc.security_group_read(fq_name=fq_name)
            self.sg_objs[name] = obj
        except NoIdError:
            return
        for vpg in obj.get_virtual_port_group_back_refs() or []:
            self.disassoc_security_group_from_vpg(name, vpg['to'])
        self.vnc.security_group_delete(fq_name=fq_name)

    def assoc_security_group_to_vpg(self, sg_name, vpg_fqname):
        sg_obj = self.sg_objs[sg_name]
        obj = self.vnc.virtual_port_group_read(fq_name=vpg_fqname)
        obj.add_security_group(sg_obj)
        self.vnc.virtual_port_group_update(obj)

    def disassoc_security_group_from_vpg(self, sg_name, vpg_fqname):
        sg_obj = self.sg_objs[sg_name]
        obj = self.vnc.virtual_port_group_read(fq_name=vpg_fqname)
        obj.del_security_group(sg_obj)
        self.vnc.virtual_port_group_update(obj)

    def assoc_port_profile_to_vpg(self, pp_name, vpg_fqname):
        pp_obj = self.pp_objs[pp_name]
        obj = self.vnc.virtual_port_group_read(fq_name=vpg_fqname)
        obj.add_port_profile(pp_obj)
        return self.vnc.virtual_port_group_update(obj)

    def disassoc_port_profile_from_vpg(self, pp_name, vpg_fqname):
        pp_obj = self.pp_objs[pp_name]
        obj = self.vnc.virtual_port_group_read(fq_name=vpg_fqname)
        obj.del_port_profile(pp_obj)
        return self.vnc.virtual_port_group_update(obj)

    def create_port_profile(self, fq_name):
        obj = PortProfile(name=fq_name[-1], parent_type='project',
                          fq_name=fq_name)
        self.vnc.port_profile_create(obj)
        return obj

    def delete_port_profile(self, fq_name):
        self.vnc.port_profile_delete(fq_name=fq_name)

    @time_taken
    def create_server_profile(self, name, fabric_name, workloads):
        fq_name = self.get_fq_name(name)
        try:
            sc_obj = self.create_storm_control_profile(fq_name)
        except RefsExistError as e:
            sc_obj = self.vnc.storm_control_profile_read(fq_name=fq_name)
        try:
            pp_obj = self.create_port_profile(fq_name)
        except RefsExistError:
            pp_obj = self.vnc.port_profile_read(fq_name=fq_name)
        self.pp_objs[name] = pp_obj
        pp_obj.add_storm_control_profile(sc_obj)
        self.vnc.port_profile_update(pp_obj)
        for workload in workloads:
            vpg_fq_name = self.get_vpg_fqname(fabric_name, workload)
            self.assoc_port_profile_to_vpg(name, vpg_fq_name)

    @time_taken
    def delete_server_profile(self, name):
        fq_name = self.get_fq_name(name)
        try:
            obj = self.vnc.port_profile_read(fq_name=fq_name)
            self.pp_objs[name] = obj
        except NoIdError:
            return
        for vpg in obj.get_virtual_port_group_back_refs() or []:
            self.disassoc_port_profile_from_vpg(name, vpg['to'])
        self.delete_port_profile(fq_name)
        try:
            self.delete_storm_control_profile(fq_name)
        except NoIdError:
            pass

    def create_storm_control_profile(self, fq_name):
        params = StormControlParameters()
        action = random.choice(['interface-shutdown', None])
        if action:
            params.set_storm_control_actions([action])
            recovery_timeout = random.randint(10, 30)
            params.set_recovery_timeout(recovery_timeout)
        params.set_bandwidth_percent(random.randint(1, 10))
        params.set_no_broadcast(random.choice([True, False]))
        params.set_no_unknown_unicast(random.choice([True, False]))
        params.set_no_multicast(random.choice([True, False]))
        #params.set_no_registered_multicast(random.choice([True, False]))
        #params.set_no_unregistered_multicast(random.choice([True, False]))
        obj = StormControlProfile(name=fq_name[-1], parent_type='project',
                                  fq_name=fq_name,
                                  storm_control_parameters=params)
        self.vnc.storm_control_profile_create(obj)
        return obj

    def delete_storm_control_profile(self, fq_name):
        return self.vnc.storm_control_profile_delete(fq_name=fq_name)

    def read_physical_router(self, name=None, fq_name=None):
        if name:
            fq_name = ['default-global-system-config', name]
        return self.vnc.physical_router_read(fq_name=fq_name)

    @time_taken
    def create_router(self, name, networks, pRouters, **kwargs):
        fq_name = self.get_fq_name(name)
        obj = LogicalRouter(name=name, parent_type='project',
                            fq_name=fq_name,
                            logical_router_type='vxlan-routing')
        for vn in networks:
            port_name = vn+'-lr-vmi'
            port_obj = self.create_port(port_name, vn,
                device_owner="network:router_interface")
            obj.add_virtual_machine_interface(port_obj)
        for pRouter in pRouters or []:
            pr_obj = self.read_physical_router(pRouter)
            obj.add_physical_router(pr_obj)
        print 'Creating LR', fq_name[-1]
        try:
            self.vnc.logical_router_create(obj)
        except RefsExistError:
            obj = self.vnc.logical_router_read(fq_name=fq_name)
        self.lr_objs[name] = obj

    def delete_router(self, name, **kwargs):
        fq_name = self.get_fq_name(name)
        try:
            obj = self.vnc.logical_router_read(fq_name=fq_name)
        except NoIdError:
            return
        try:
            self.vnc.logical_router_delete(fq_name=fq_name)
        except NoIdError:
            pass
        for vmi in obj.get_virtual_machine_interface_refs() or []:
            self.delete_port(id=vmi['uuid'])
        print 'Deleted LR', fq_name[-1]

    def update_routed_vn_properties(self, vn, lr, routers,
                                    import_policy, export_policy):
        vn_obj = self.get_network_obj(vn)
        cidr = self.get_network(vn)['cidr']
        lr_obj = self.lr_objs[lr]
        vn_routed_properties = VirtualNetworkRoutedPropertiesType()
        bgp_params = BgpParameters(
            peer_autonomous_system=random.randint(20000, 50000),
            peer_ip_address=get_an_ip(cidr, 1),
            hold_time=90)
        rp_params = RoutingPolicyParameters(
            import_routing_policy_uuid=[import_policy.uuid],
            export_routing_policy_uuid=[export_policy.uuid])
        for index, router in enumerate(routers):
            pr_obj = self.read_physical_router(router)
            routed_properties = RoutedProperties(
                logical_router_uuid=lr_obj.uuid,
                physical_router_uuid=pr_obj.uuid,
                routed_interface_ip_address=get_an_ip(cidr, 2+index),
                routing_protocol='bgp',
                bgp_params=bgp_params,
                bfd_params=BfdParameters(
                    time_interval=10,
                    detection_time_multiplier=4),
                routing_policy_params=rp_params)
            vn_routed_properties.add_routed_properties(routed_properties)
        vn_obj.set_virtual_network_routed_properties(vn_routed_properties)
        return self.vnc.virtual_network_update(vn_obj)

    def create_routing_policy(self, name):
        fq_name = self.get_fq_name(name)
        obj = RoutingPolicy(name, parent_type='project', fq_name=fq_name)
        obj.set_routing_policy_entries(PolicyStatementType(
            term=[PolicyTermType(
                term_match_condition=TermMatchConditionType(['direct',
                                                             'static']),
                term_action_list=TermActionListType(action='accept'))]))
        try:
            self.vnc.routing_policy_create(obj)
        except RefsExistError:
            obj = self.vnc.routing_policy_read(fq_name=fq_name)
        return obj

    def delete_routing_policy(self, name):
        fq_name = self.get_fq_name(name)
        try:
            self.vnc.routing_policy_delete(fq_name=fq_name)
        except NoIdError:
            pass

    def create_unmanaged_instance(self, name, fabric_name, external_peer,
                                  left_vlan, right_vlan, left_networks,
                                  right_networks, pRouters):
        left_vn = name+'-left-vn'; right_vn = name+'-right-vn'
        left_lr = name+'-left-lr'; right_lr = name+'-right-lr'
        self.create_network(left_vn, get_random_cidr(), left_vlan, routed=True)
        self.create_network(right_vn, get_random_cidr(), right_vlan, routed=True)
        vpg_name = external_peer['name']
        pifs = external_peer['pifs']
        self.create_workload(vpg_name, pifs, [left_vn, right_vn], fabric_name)
        self.create_router(left_lr, left_networks+[left_vn], pRouters)
        self.create_router(right_lr, right_networks+[right_vn], pRouters)
        import_policy = self.create_routing_policy(name+'-import-rp')
        export_policy = self.create_routing_policy(name+'-export-rp')
        border_routers = list()
        for pif in pifs:
            border_routers.append(pif.split(':')[0])
            self.update_routed_vn_properties(left_vn, left_lr, border_routers,
                import_policy, export_policy)
            self.update_routed_vn_properties(right_vn, right_lr, border_routers,
                import_policy, export_policy)

    def delete_unmanaged_instance(self, name, fabric_name, external_peer):
        left_vn = name+'-left-vn'; right_vn = name+'-right-vn'
        left_lr = name+'-left-lr'; right_lr = name+'-right-lr'
        self.delete_router(left_lr)
        self.delete_router(right_lr)
        self.delete_routing_policy(name+'-import-rp')
        self.delete_routing_policy(name+'-export-rp')
        vpg_name = external_peer['name']
        self.delete_workload(vpg_name, fabric_name)
        self.delete_network(left_vn)
        self.delete_network(right_vn)

    def get_rt_of_vn(self, fq_name):
        ri_fqname = fq_name + fq_name[-1:]
        for i in range(30):
            ri_obj = self.vnc.routing_instance_read(fq_name=ri_fqname)
            targets = list()
            for rt in ri_obj.get_route_target_refs() or []:
                targets.extend(rt['to'])
            if not targets:
                time.sleep(1)
                continue
            return targets

    def get_vmi_ip_mac(self, **kwargs):
        vmi_obj = self.read_port(**kwargs)
        mac = vmi_obj.get_virtual_machine_interface_mac_addresses().mac_address[0]
        for iip in vmi_obj.get_instance_ip_back_refs() or []:
            iip_obj = self.vnc.instance_ip_read(id=iip['uuid'])
            return iip_obj.instance_ip_address, mac
        return None, mac

    def read_fabric(self, name):
        fq_name = ['default-global-system-config', name]
        return self.vnc.fabric_read(fq_name=fq_name)

    @time_taken
    def execute_job(self, template_fqname, payload_dict, devices=None):
        kwargs = {'job_template_fq_name': template_fqname,
                  'job_input': payload_dict}
        if devices:
            kwargs['device_list'] = devices
        print 'Executing Job: %s'%':'.join(template_fqname)
        resp = self.vnc.execute_job(**kwargs)
        execution_id = resp['job_execution_id']
        assert self.wait_for_job_to_finish(':'.join(template_fqname),
            execution_id), "Job Execution failed"

    def read_overlay_role(self, role):
        return self.vnc.overlay_role_read(
            fq_name=['default-global-system-config', role])

    def read_physical_role(self, role):
        return self.vnc.physical_role_read(
            fq_name=['default-global-system-config', role])

    def read_virtual_router(self, name=None, **kwargs):
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        return self.vnc.virtual_router_read(**kwargs)

    def associate_rb_role(self, prouter, rb_role):
        prouter_obj = self.read_physical_router(fq_name=prouter)
        role_obj = self.read_overlay_role(rb_role)
        prouter_obj.add_overlay_role(role_obj)
        self.vnc.physical_router_update(prouter_obj)

    def associate_physical_role(self, prouter, role):
        prouter_obj = self.read_physical_router(fq_name=prouter)
        role_obj = self.read_physical_role(role)
        prouter_obj.add_physical_role(role_obj)
        self.vnc.physical_router_update(prouter_obj)

    def associate_csn(self, prouter, csn):
        csns = csn if isinstance(csn, list) else [csn]
        prouter_obj = self.read_physical_router(fq_name=prouter)
        for vrouter in csns:
            vr_obj = self.read_virtual_router(vrouter)
            prouter_obj.add_virtual_router(vr_obj)
        self.vnc.physical_router_update(prouter_obj)

    def onboard(self, fabric_name, asn=64512, addresses=None, ep_style=True,
                disable_validation=True, **kwargs):
        try:
            fabric = self.read_fabric(fabric_name)
            for kvp in fabric.get_annotations().get_key_value_pair():
                if kvp.key.lower() == 'user_input':
                    payload = json.loads(kvp.value)
                    break
        except NoIdError:
            payload = {'fabric_fq_name': ["default-global-system-config",
                                          fabric_name],
                       'node_profiles': [{"node_profile_name": profile}
                           for profile in NODE_PROFILES],
                       'device_auth': [],
                       'overlay_ibgp_asn': asn,
                       'loopback_subnets': ["1.126.127.0/24"],
                       'enterprise_style': ep_style,
                       'disable_vlan_vn_uniqueness_check': disable_validation
                      }
        payload.pop('supplemental_day_0_cfg', None)
        payload.pop('import_configured', None)
        payload.pop('device_to_ztp', None)
        payload['device_auth'].append({"username": USERNAME,
                                       "password": PASSWORD})
        cidrs = [{"cidr": "%s/32"%IPAddress(addr)} for addr in addresses]
        payload['management_subnets'] = cidrs
        fq_name = ['default-global-system-config',
                   'existing_fabric_onboard_template']
        self.execute_job(fq_name, payload)

    def assign_roles(self, fabric_name, spines=None, leafs=None,
                     bleafs=None, clos_type='erb', **kwargs):
        roles = list()
        for leaf in leafs or []:
            fq_name = ['default-global-system-config', leaf]
            if clos_type == 'erb':
                rb_roles = ['ERB-UCAST-Gateway']
            else:
                rb_roles = ['CRB-Access']
            roles.append({'device_fq_name': fq_name,
                          'physical_role': 'leaf',
                          'routing_bridging_roles': rb_roles})
        for spine in spines or []:
            fq_name = ['default-global-system-config', spine]
            if clos_type == 'erb':
                rb_roles = ['lean', 'Route-Reflector']
            else:
                rb_roles = ['CRB-Gateway', 'Route-Reflector']
            roles.append({'device_fq_name': fq_name,
                          'physical_role': 'spine',
                          'routing_bridging_roles': rb_roles})
        for bleaf in bleafs or []:
            fq_name = ['default-global-system-config', bleaf]
            rb_roles = ['DC-Gateway', 'DCI-Gateway']
            roles.append({'device_fq_name': fq_name,
                          'physical_role': 'leaf',
                          'routing_bridging_roles': rb_roles})
        for spine in spines or []:
            fq_name = ['default-global-system-config', spine]
        if not roles:
            raise Exception('Unable to find any device to assign roles')
        fq_name = ['default-global-system-config', 'role_assignment_template']
        payload = {'fabric_fq_name': ['default-global-system-config',
                                      fabric_name],
                   'role_assignments': roles}
        for device_roles in payload['role_assignments']:
            device = device_roles['device_fq_name']
            self.associate_physical_role(device,
                device_roles['physical_role'])
            for role in device_roles['routing_bridging_roles']:
                if role.lower() in VALID_OVERLAY_ROLES:
                    self.associate_rb_role(device, role.lower())
        self.execute_job(fq_name, payload)

    def delete_fabric(self, fabric_name):
        fq_name = ['default-global-system-config', 'fabric_deletion_template']
        payload = {'fabric_fq_name': ["default-global-system-config",
                                      fabric_name]}
        self.execute_job(fq_name, payload)

    def add_csn(self, devices, **kwargs):
        if not self.csn:
            return
        for device in devices:
            fq_name = ['default-global-system-config', device]
            self.associate_csn(fq_name, self.csn)

class AnalyticsApi(RestServer):
    def __init__(self, server, token=None, use_ssl=None):
        super(AnalyticsApi, self).__init__(server, 8081, token, use_ssl)

    def post_query(self, table, start_time='now-10m', end_time='now',
                   where_clause='', select_fields=None):
        res = []
        query_dict = {'table': table,
                      'start_time': start_time,
                      'end_time': end_time,
                      'select_fields': select_fields,
                      'where': where_clause
                     }
        resp = self.post('analytics/query', query_dict)
        if resp is not None and 'value' in resp:
            for item in resp['value']:
                res.append(item)
            return res
