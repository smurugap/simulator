from scripts.contrail_api import ConfigApi, AnalyticsApi
from scripts.agent_api import SimulatorAgentApi
from collections import deque, defaultdict
from common.constants import *
from common.orderedset import OrderedSet
from common.util import GeventLib, get_random_cidr, custom_dict
import argparse
import yaml
import sys
import time
advertise_route = False

def generate_expected(f):
    def wrapper(self, *args, **kwargs):
        if getattr(self, 'generated', None) is not True:
            self._generate_expected_networks()
            self._generate_expected_workloads()
            self._generate_expected_gateways()
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
        self.agent_h = SimulatorAgentApi()
        self.gpool = GeventLib(threads)

    def create_simulators(self):
        for fabric_name, details in self.fabrics.items():
            interface = details['interface']
            cidr = details['mgmt_subnet']
            gw = details['gateway']
            address_pool = details.get('address_pool') or []
            n_leafs = details.get('leaf', {}).get('count', 0)
            n_spines = details.get('spine', {}).get('count', 0)
            n_pifs = details.get('leaf', {}).get('pifs') or DEFAULT_PIFS
            if self.get_simulators(fabric_name):
                self.agent_h.update_fabric(fabric_name, address_pool,
                    n_leafs, n_spines, n_pifs, self.collector)
            else:
                self.agent_h.create_fabric(fabric_name, interface, cidr,
                    gw, address_pool, n_leafs, n_spines, n_pifs,
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
            leafs = list(); spines = list()
            for prouter, info in self.prouters[fabric_name].items():
                if info['role'] == 'leaf':
                    leafs.append(prouter)
                else:
                    spines.append(prouter)
            self.client_h.assign_roles(fabric_name, spines, leafs, clos)

    def start_sflows(self, n_flows=None, fabric=None, refresh_interval=5):
        seconds = refresh_interval * 60
        direction = self.sflow_args.get('direction') or 'ingress'
        n_leafs = self.fabrics[fabric]['leaf']['count']
        n_vpgs = self.fabrics[fabric]['overlay']['vpg']
        n_bms_per_router = (n_vpgs/n_leafs) * 2
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

    def create(self):
        self.stage2()
        self.stage3()

    def delete(self):
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
            n_pifs = details['leaf'].get('pifs') or DEFAULT_PIFS
            n_spines = details['spine'].get('count') or 0
            for index in range(n_spines, n_pifs):
                for prouter in prouters:
                    pif_name = ":".join([prouter, 'et-0/0/%s'%index])
                    pifs.add(pif_name)
        return pifs

    def get_ports(self, fabric, count=2):
        return [self.physical_interfaces[fabric].pop() for x in range(count)]

    def _get_ports_per_vn(self, overlay):
        total_lifs = overlay['vlan_per_vpg'] * overlay['vpg']
        return ((total_lifs-1)/overlay['networks'])+1

    def _get_vns_for_lr(self, fabric, n_vns):
        vns = list()
        for network in self.fabric_networks[fabric]:
            info = self.networks[network]
            if info['lr'] == False:
                vns.append(network)
                info['lr'] = True
            if len(vns) == n_vns:
                break
        return vns

    def _get_pRouters_for_lr(self, fabric):
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

    def _get_vns_for_vpg(self, fabric, n_vlans, max_ports_per_vn):
        vns = list()
        for network in self.fabric_networks[fabric]:
            info = self.networks[network]
            if info['count'] < max_ports_per_vn:
                vns.append(network)
                info['count'] += 1
            if len(vns) == n_vlans:
                break
        return vns

    def _generate_expected_gateways(self):
        self.routers = dict()
        for fabric_name, details in self.fabrics.items():
            overlay = details['overlay']
            n_vns = overlay.get('vns_per_lr') or 0
            for index in range(overlay.get('logical_routers') or 0):
                name = self.get_name(fabric_name, 'router', index)
                networks = self._get_vns_for_lr(fabric_name, n_vns)
                pRouters = self._get_pRouters_for_lr(fabric_name)
                self.routers[name] = {'pRouters': pRouters,
                                      'networks': networks}

    def _generate_expected_workloads(self):
        self.port_groups = dict()
        for fabric_name, details in self.fabrics.items():
            overlay = details['overlay']
            n_vlans = overlay['vlan_per_vpg']
            ports_per_vn = self._get_ports_per_vn(overlay)
            for index in range(overlay.get('vpg') or 0):
                name = self.get_name(fabric_name, 'vpg', index)
                pifs = self.get_ports(fabric_name)
                networks = self._get_vns_for_vpg(fabric_name, n_vlans,
                                                 ports_per_vn)
                self.port_groups[name] = {'pifs': pifs,
                                          'networks': networks,
                                          'fabric': fabric_name}

    def _generate_expected_networks(self):
        self.networks = dict()
        self.fabric_networks = dict()
        for fabric_name, details in self.fabrics.items():
            overlay = details['overlay']
            self.fabric_networks[fabric_name] = OrderedSet()
            for index in range(overlay.get('networks') or 0):
                name = self.get_name(fabric_name, 'network', index)
                cidr = get_random_cidr(mask=DEFAULT_OVERLAY_SUBNET_MASK)
                self.networks[name] = {'vlan': index+2,
                                       'cidr': cidr,
                                       'fabric': fabric_name,
                                       'count': 0,
                                       'lr': False}
                self.fabric_networks[fabric_name].add(name)

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
