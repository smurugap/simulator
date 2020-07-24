from scripts.contrail_api import ConfigApi, AnalyticsApi
from scripts.agent_api import SimulatorAgentApi
from collections import deque, defaultdict
from common.constants import *
from common.orderedset import OrderedSet
from common.util import GeventLib, get_random_cidr, custom_dict, get_random_ip
import argparse
import yaml
import sys
import time
import random
import warnings
warnings.filterwarnings("ignore")

advertise_route = False

IP_PROTO_FILTER = ['TCP', 'UDP', 'ICMP', 'ANY']

def generate_expected(f):
    def wrapper(self, *args, **kwargs):
        if getattr(self, 'generated', None) is not True:
            self.generate_expected_networks()
            self.generate_expected_workloads()
            self.generate_expected_gateways()
            self.generate_expected_filters()
            self.generate_expected_server_profiles()
            self.generate_expected_unmanaged_instances()
            self.generated = True
        return f(self, *args, **kwargs)
    return wrapper

class Scale(object):
    def __init__ (self, username, password, project_name='admin',
                  domain_name='Default', auth_host=None, contrail_args=None,
                  fabric_args=None, sflow_args=None, threads=1):
        if contrail_args:
            self.client_h = ConfigApi(username, password, project_name,
                domain_name, auth_host=auth_host, contrail_args=contrail_args)
        self.sflow_args = sflow_args
        self.collector = sflow_args.get('server')
        self.fabrics = fabric_args
        self.threads = threads
        self.prouters = custom_dict(self.get_simulators)
        self.physical_interfaces = custom_dict(self.get_physical_interfaces)
        self.ext_peer_pifs = custom_dict(self.get_ext_peer_pifs)
        self.agent_h = SimulatorAgentApi()
        self.gpool = GeventLib(threads)

    def create_simulators(self):
        for fabric_name, details in self.fabrics.items():
            interface = details['interface']
            cidr = details['mgmt_subnet']
            gw = details['gateway']
            address_pool = details.get('address_pool') or []
            n_leafs = details.get('leaf', 0)
            n_spines = details.get('spine', 0)
            n_pifs = details.get('pifs') or DEFAULT_PIFS
            n_border_leafs = details.get('border_leaf', 0)
            if self.get_simulators(fabric_name):
                self.agent_h.update_fabric(fabric_name, address_pool,
                    n_leafs, n_spines, n_border_leafs, n_pifs, self.collector)
            else:
                self.agent_h.create_fabric(fabric_name, interface, cidr,
                    gw, address_pool, n_leafs, n_spines, n_border_leafs, n_pifs,
                    self.collector)

    def get_simulators(self, fabric_name):
        return self.agent_h.get_fabric(fabric_name)

    def onboard_fabric(self):
        for fabric_name, details in self.fabrics.items():
            addr = list()
            for prouter, info in self.prouters[fabric_name].items():
                addr.append(info['address'])
            asn = details.get('asn') or DEFAULT_OVERLAY_ASN
            self.client_h.onboard(fabric_name, asn, addr)

    def assign_roles(self):
        for fabric_name, details in self.fabrics.items():
            clos = details.get('clos', DEFAULT_CLOS_TYPE)
            leafs = list(); spines = list(); bleafs = list()
            for prouter, info in self.prouters[fabric_name].items():
                if info['role'] == 'leaf':
                    leafs.append(prouter)
                elif info['role'] == 'bleaf':
                    bleafs.append(prouter)
                else:
                    spines.append(prouter)
            self.client_h.assign_roles(fabric_name, spines, leafs, bleafs, clos)

    def start_sflows(self, n_flows=None, fabric=None, refresh_interval=5):
        seconds = refresh_interval * 60
        direction = self.sflow_args.get('direction') or 'ingress'
        n_leafs = self.fabrics[fabric]['leaf']
        import pdb; pdb.set_trace()
        n_vpgs = self.fabrics[fabric]['overlay'][0]['vpg']
        n_bms_per_router = (((n_vpgs-1)/n_leafs)+1) * 2
        print 'Will generate sflows every %s seconds'%seconds
        print 'Press ctrl+c to stop flow generation'
        while True:
            try:
                self.agent_h.start_sflows(fabric, direction,
                                          n_bms_per_router, n_flows)
                time.sleep(seconds)
            except Exception as e:
                print e.message
                self.stop_sflows(fabric)
                break

    def stop_sflows(self, fabric=None):
        self.agent_h.stop_sflows(fabric)

    def stage1(self):
        self.create_simulators()
        print 'Sleeping for 60 seconds before onboarding'
        time.sleep(60)
        self.onboard_fabric()
        self.assign_roles()

    def add_csn(self):
        for fabric_name, details in self.fabrics.items():
            self.client_h.add_csn()

    def delete_fabric(self):
        for fabric_name, details in self.fabrics.items():
            self.client_h.delete_fabric(fabric_name)

    def delete_simulators(self):
        for fabric_name, details in self.fabrics.items():
            self.agent_h.delete_fabric(fabric_name)

    def get_name(self, prefix, obj_type, index):
        return "%s-%s%s"%(prefix, obj_type, index)

    @generate_expected
    def create_networks(self):
        args_list = list()
        for name, info in self.networks.items():
            kwargs = {'cidr': info['cidr'],
                      'vlan': info['vlan']}
            args_list.append([(name,), kwargs])
        results = self.gpool.spawn(self.client_h.create_network, args_list)
        for result in results:
            self.networks[result['name']].update(result or {})

    @generate_expected
    def create_workloads(self):
        args_list = list()
        for name, info in self.port_groups.items():
            kwargs = {'pifs': info['pifs'],
                      'networks': info['networks'],
                      'fabric_name': info['fabric']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.create_workload, args_list)

    def stage2(self):
        self.create_networks()
        self.create_workloads()

    @generate_expected
    def delete_networks(self):
        args_list = list()
        for name, info in self.networks.items():
            args_list.append([(name,), dict()])
        self.gpool.spawn(self.client_h.delete_network, args_list)

    @generate_expected
    def delete_workloads(self):
        args_list = list()
        for name, info in self.port_groups.items():
            kwargs = {'pifs': info['pifs'],
                      'networks': info['networks'],
                      'fabric_name': info['fabric']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.delete_workload, args_list)

    def delete_stage2(self):
        self.delete_workloads()
        self.delete_networks()

    @generate_expected
    def create_routers(self):
        args_list = list()
        for name, info in self.routers.items():
            kwargs = {'pRouters': info['pRouters'],
                      'networks': info['networks']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.create_router, args_list)

    def stage3(self):
        self.create_routers()

    @generate_expected
    def delete_routers(self):
        args_list = list()
        for name, info in self.routers.items():
            kwargs = {'pRouters': info['pRouters'],
                      'networks': info['networks']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.delete_router, args_list)

    def delete_stage3(self):
        self.delete_routers()

    @generate_expected
    def create_firewall_filters(self):
        args_list = list()
        for name, info in self.filters.items():
            kwargs = {'fabric_name': info['fabric'],
                      'workloads': info['workloads'],
                      'rules': info['rules']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.create_firewall_filter, args_list)

    @generate_expected
    def delete_firewall_filters(self):
        args_list = list()
        for name, info in self.filters.items():
            kwargs = dict()
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.delete_firewall_filter, args_list)

    @generate_expected
    def create_server_profiles(self):
        args_list = list()
        for name, info in self.server_profiles.items():
            kwargs = {'fabric_name': info['fabric'],
                      'workloads': info['workloads']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.create_server_profile, args_list)

    @generate_expected
    def delete_server_profiles(self):
        args_list = list()
        for name, info in self.server_profiles.items():
            kwargs = dict()
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.delete_server_profile, args_list)

    def stage4(self):
        self.create_firewall_filters()
        self.create_server_profiles()

    def delete_stage4(self):
        self.delete_firewall_filters()
        self.delete_server_profiles()

    @generate_expected
    def create_unmanaged_instances(self):
        args_list = list()
        for name, info in self.unmanaged_instances.items():
            kwargs = {'fabric_name': info['fabric'],
                      'external_peer': info['external_peer'],
                      'left_vlan': info['left_vlan'],
                      'right_vlan': info['right_vlan'],
                      'left_networks': info['left_vns'],
                      'right_networks': info['right_vns'],
                      'pRouters': info['pRouters']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.create_unmanaged_instance, args_list)

    @generate_expected
    def delete_unmanaged_instances(self):
        args_list = list()
        for name, info in self.unmanaged_instances.items():
            kwargs = {'fabric_name': info['fabric'],
                      'external_peer': info['external_peer']}
            args_list.append([(name,), kwargs])
        self.gpool.spawn(self.client_h.delete_unmanaged_instance, args_list)

    def stage5(self):
        self.create_unmanaged_instances()

    def delete_stage5(self):
        self.delete_unmanaged_instances()

    def create(self):
        self.stage2()
        self.stage3()
        self.stage4()
        self.stage5()

    def delete(self):
        self.delete_stage5()
        self.delete_stage4()
        self.delete_stage3()
        self.delete_stage2()

    def get_physical_interfaces(self, fabric_name):
        if fabric_name not in self.physical_interfaces:
            pifs = OrderedSet()
            prouters = list()
            for prouter, info in self.prouters[fabric_name].items():
                if info['role'] == 'leaf':
                    prouters.append(prouter)
            details = self.fabrics[fabric_name]
            n_pifs = details.get('pifs') or DEFAULT_PIFS
            n_spines = details.get('spine') or 0
            for index in range(n_spines, n_pifs):
                for prouter in prouters:
                    pif_name = ":".join([prouter, 'et-0/0/%s'%index])
                    pifs.add(pif_name)
            return pifs

    def get_ext_peer_pifs(self, fabric_name):
        if fabric_name not in self.ext_peer_pifs:
            pifs = OrderedSet()
            prouters = list()
            details = self.fabrics[fabric_name]
            clos = details.get('clos', DEFAULT_CLOS_TYPE)
            n_spines = details['spine']
            n_leafs = details['leaf']
            n_pifs = details.get('pifs') or DEFAULT_PIFS
            pif_start = n_pifs
            for prouter, info in self.prouters[fabric_name].items():
                if clos == 'erb' and info['role'] == 'bleaf':
                    prouters.append(prouter)
                    pif_start = n_spines
                elif clos == 'crb' and info['role'] == 'spine':
                    prouters.append(prouter)
                    pif_start = n_leafs
                    n_pifs = n_leafs + n_pifs
            for index in range(pif_start, n_pifs):
                for prouter in prouters:
                    pif_name = ":".join([prouter, 'et-0/0/%s'%index])
                    pifs.add(pif_name)
            return pifs

    def get_ports(self, fabric, count=2):
        try:
            return [self.physical_interfaces[fabric].pop() for x in range(count)]
        except KeyError:
            return list()

    def get_ext_ports(self, fabric, count=2):
        try:
            return [self.ext_peer_pifs[fabric].pop() for x in range(count)]
        except KeyError:
            return list()

    def get_ports_per_vn(self, overlay):
        total_lifs = overlay['vlan_per_vpg'] * overlay['vpg']
        return ((total_lifs-1)/overlay['networks'])+1

    def get_vns_for_lr(self, pname, n_vns):
        vns = list()
        for network in self.fabric_networks[pname]:
            info = self.networks[network]
            if info['lr'] == False:
                vns.append(network)
                info['lr'] = True
            if len(vns) == n_vns:
                break
        return vns

    def get_pRouters_for_lr(self, fabric):
        devices = list()
        details = self.fabrics[fabric]
        leafs = list(); spines = list()
        for prouter, info in self.prouters[fabric].items():
            if info['role'] == 'leaf':
                leafs.append(prouter)
            else:
                spines.append(prouter)
        clos = details.get('clos', DEFAULT_CLOS_TYPE)
        if clos == 'erb':
            return leafs
        else:
            return spines

    def get_vns_for_vpg(self, pname, n_vlans, max_ports_per_vn):
        vns = list()
        for network in self.fabric_networks[pname]:
            info = self.networks[network]
            if info['count'] < max_ports_per_vn:
                vns.append(network)
                info['count'] += 1
            if len(vns) == n_vlans:
                break
        return vns

    def get_rules_for_filters(self, count=3):
        rules = list()
        for i in range(0, count):
            cidr = None
            rules.append({'dst_ip': get_random_ip(cidr),
                          'dst_port': random.randint(20, 2000),
                          'protocol': random.choice(IP_PROTO_FILTER)})
        return rules

    def get_port_groups_for_filters(self, pname, n_vpgs):
        workloads = list()
        for name in self.fabric_workloads[pname]:
            info = self.port_groups[name]
            if info['filters'] is False:
                workloads.append(name)
                info['filters'] = True
            if len(workloads) == n_vpgs:
                break
        return workloads

    def get_port_groups_for_server_profiles(self, pname, n_vpgs):
        workloads = list()
        for name in self.fabric_workloads[pname]:
            info = self.port_groups[name]
            if info['server_profiles'] is False:
                workloads.append(name)
                info['server_profiles'] = True
            if len(workloads) == n_vpgs:
                break
        return workloads

    def get_port_group_name(self, pifs):
        name = ''
        for pif in pifs:
            prouter, intf = pif.split(':')
            name = "%s%s-%s"%('%s_'%name if name else '', prouter,
                              intf.split("/")[-1])
        return name

    def get_profile_name(self, fabric_name, overlay):
        return '-'.join([fabric_name, overlay['name']])

    def generate_expected_unmanaged_instances(self):
        self.unmanaged_instances = dict()
        for fabric_name, details in self.fabrics.items():
            clos = details.get('clos', DEFAULT_CLOS_TYPE)
            for overlay in details.get('overlay') or []:
                pname = self.get_profile_name(fabric_name, overlay)
                if not overlay.get('unmanaged_devices'):
                    continue
                ext_peers = overlay['unmanaged_devices']
                n_instances_per_peer = ext_peers['instances_per_device']
                n_vns = ext_peers['vns_per_instance']
                prouters = set()
                for prouter, info in self.prouters[fabric_name].items():
                    if clos == 'erb' and info['role'] == 'bleaf':
                        prouters.add(prouter)
                    elif clos == 'crb' and info['role'] == 'spine':
                        prouters.add(prouter)
                vlan = 4094
                for peer_index in range(ext_peers['count']):
                    pifs = self.get_ext_ports(fabric_name)
                    if not pifs:
                        return
                    peer_name = self.get_port_group_name(pifs)
                    for pif in pifs:
                        prouters.add(pif.split(':')[0])
                    for index in range(n_instances_per_peer):
                        name = self.get_name(pname,
                            'peer%s-lr'%peer_index, index)
                        left_networks = self.get_vns_for_lr(pname, n_vns)
                        right_networks = self.get_vns_for_lr(pname, n_vns)
                        self.unmanaged_instances[name] = {
                            'left_vlan': vlan - 1,
                            'right_vlan': vlan - 2,
                            'left_vns': left_networks,
                            'right_vns': right_networks,
                            'fabric': fabric_name,
                            'pRouters': list(prouters),
                            'external_peer': {'name': peer_name, 'pifs': pifs}
                        }
                        vlan = vlan - 2

    def generate_expected_server_profiles(self):
        self.server_profiles = dict()
        for fabric_name, details in self.fabrics.items():
            for overlay in details.get('overlay') or []:
                pname = self.get_profile_name(fabric_name, overlay)
                for index in range(overlay.get('storm_control_profiles') or 0):
                    n_vpgs = overlay['vpg']/overlay['storm_control_profiles']
                    name = self.get_name(pname, 'server_profile', index)
                    workloads = self.get_port_groups_for_server_profiles(
                        pname, n_vpgs)
                    self.server_profiles[name] = {'fabric': fabric_name,
                                                  'workloads': workloads}

    def generate_expected_filters(self):
        self.filters = dict()
        for fabric_name, details in self.fabrics.items():
            for overlay in details.get('overlay') or []:
                pname = self.get_profile_name(fabric_name, overlay)
                for index in range(overlay.get('firewall_filters') or 0):
                    n_vpgs = overlay['vpg']/overlay['firewall_filters']
                    name = self.get_name(pname, 'filter', index)
                    workloads = self.get_port_groups_for_filters(pname,
                                                                 n_vpgs)
                    rules = self.get_rules_for_filters(count=3)
                    self.filters[name] = {'fabric': fabric_name,
                                          'workloads': workloads,
                                          'rules': rules}

    def generate_expected_gateways(self):
        self.routers = dict()
        for fabric_name, details in self.fabrics.items():
            for overlay in details.get('overlay') or []:
                pname = self.get_profile_name(fabric_name, overlay)
                n_vns = overlay.get('vns_per_lr') or 0
                for index in range(overlay.get('logical_routers') or 0):
                    name = self.get_name(pname, 'router', index)
                    networks = self.get_vns_for_lr(pname, n_vns)
                    pRouters = self.get_pRouters_for_lr(fabric_name)
                    self.routers[name] = {'pRouters': pRouters,
                                          'networks': networks}

    def generate_expected_workloads(self):
        self.port_groups = dict()
        self.fabric_workloads = dict()
        for fabric_name, details in self.fabrics.items():
            for overlay in details.get('overlay') or []:
                n_vlans = overlay['vlan_per_vpg']
                pname = self.get_profile_name(fabric_name, overlay)
                ports_per_vn = self.get_ports_per_vn(overlay)
                self.fabric_workloads[pname] = OrderedSet()
                for index in range(overlay.get('vpg') or 0):
                    pifs = self.get_ports(fabric_name)
                    if not pifs:
                        return
                    name = self.get_port_group_name(pifs)
                    networks = self.get_vns_for_vpg(pname, n_vlans,
                                                     ports_per_vn)
                    self.port_groups[name] = {'pifs': pifs,
                                              'networks': networks,
                                              'filters': False,
                                              'server_profiles': False,
                                              'fabric': fabric_name}
                    self.fabric_workloads[pname].add(name)

    def generate_expected_networks(self):
        self.networks = dict()
        self.fabric_networks = dict()
        for fabric_name, details in self.fabrics.items():
            for overlay in details.get('overlay') or []:
                pname = self.get_profile_name(fabric_name, overlay)
                self.fabric_networks[pname] = OrderedSet()
                for index in range(overlay.get('networks') or 0):
                    name = self.get_name(pname, 'network', index)
                    cidr = get_random_cidr(mask=DEFAULT_OVERLAY_SUBNET_MASK)
                    self.networks[name] = {'vlan': index+2,
                                           'cidr': cidr,
                                           'fabric': fabric_name,
                                           'count': 0,
                                           'lr': False}
                    self.fabric_networks[pname].add(name)

def parse_cli(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--input', required=True, metavar="FILE",
        help='location of the yaml template file')
    parser.add_argument('-o', '--oper', default='add',
        help='Operation to perform (add/delete)')
    parser.add_argument('-t', '--threads', default=1, type=int,
        help='No of parallel threads to use for overlay object creation')
    parser.add_argument('-c', '--custom-args',
        help='Any custom args to pass to function')
    pargs = parser.parse_args(args)
    return pargs

def main(template, oper, custom_args, threads):
    with open(template, 'r') as fd:
        try:
            yargs = yaml.load(fd, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            print exc
            raise
    keystone_args = yargs['keystone']
    username = keystone_args['username']
    password = keystone_args['password']
    project = keystone_args.get('project', 'admin')
    domain = keystone_args.get('domain', 'Default')
    auth_host = keystone_args.get('server')
    obj = Scale(username, password, project, domain, auth_host,
                yargs.get('contrail'), yargs.get('fabrics'),
                yargs.get('sflow'), threads)
    if oper.lower() == 'del':
        obj.delete()
    elif oper.lower() == 'add':
        obj.create()
    elif getattr(obj, oper.lower(), None):
        kwargs = dict()
        if custom_args:
            kwargs = dict(x.strip().split('=') for x in custom_args.split(","))
        fn = getattr(obj, oper.lower())
        fn(**kwargs)
    else:
        raise Exception()

if __name__ == '__main__':
    pargs = parse_cli(sys.argv[1:])
    main(pargs.input, pargs.oper, pargs.custom_args, pargs.threads)
