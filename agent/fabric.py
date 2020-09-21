import ast
from flask import jsonify
from collections import defaultdict
from common.docker_api import docker_h
from common.ipc_api import send_event
from netaddr import IPNetwork, IPAddress
from common.util import get_available_ips, convert_template, \
                        GeventLib, delete_file, CONFDIR, get_file
from common.exceptions import InvalidUsage
import os

MYDIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(MYDIR, 'simulator.conf.j2')
ENV_SIMULATOR = {'MODE': 'simulator'}

class Fabric(object):
    """ Fabric wide operations - Create/Update/Delete/Get simulators """
    @classmethod
    def _get(self, fabric_name=None):
        """ Get list of containers belonging to the fabric """
        fabrics = defaultdict(dict)
        for name, details in docker_h.list_containers(fabric_name).items():
            fabric = details.pop('fabric', None)
            if not fabric:
                continue
            fabrics[fabric].update({name: details})
        return fabrics

    @classmethod
    def get(self, fabric_name=None):
        return jsonify({'fabrics': self._get(fabric_name)})

    @classmethod
    def delete(self, fabric_name):
        """ Delete the corresponding fabric """
        self.containers = docker_h.list_containers(fabric_name,
                               all=True)
        GeventLib(10).map(self._delete, list(self.containers.keys()))
        network = '-'.join([fabric_name, 'Network'])
        docker_h.delete_network(network)

    @classmethod
    def _delete(self, device):
        docker_h.delete_container(self.containers[device]['id'])
        delete_file(self.get_file(device, ftype='conf'))
        delete_file(self.get_file(device, ftype='sflows'))
        delete_file(self.get_file(device, ftype='oids'))
        delete_file(self.get_file(device, engine='netconf'))
        delete_file(self.get_file(device, engine='openconfig'))
        delete_file(self.get_file(device, engine='snmp'))
        delete_file(self.get_file(device, engine='syslog'))
        try:
            absname = os.path.join(CONFDIR, device)
            os.rmdir(absname)
        except OSError:
            pass
 
    @classmethod
    def get_file(self, device, engine=None, ftype='sock'):
        return get_file(device, engine, ftype)

    def launch_containers(self):
        for index in range(self.n_spines):
            name = '-'.join([self.fabric, 'Spine%s'%index])
            pifs = self.n_leafs + self.n_pifs
            self.launch_container(name, 'spine', pifs)

        for index in range(self.n_leafs):
            name = '-'.join([self.fabric, 'Leaf%s'%index])
            self.launch_container(name, 'leaf', self.n_pifs)

        for index in range(self.n_border_leafs):
            name = '-'.join([self.fabric, 'BLeaf%s'%index])
            self.launch_container(name, 'bleaf', self.n_pifs)

        for index in range(self.n_super_spines):
            name = '-'.join([self.fabric, 'SuperSpine%s'%index])
            self.launch_container(name, 'super_spine', self.n_pifs)

    def create_template(self, name, role, n_pifs):
        sflows_filename = self.get_file(name, ftype='sflows')
        snmp_oids = self.get_file(name, ftype='oids')
        nsock = self.get_file(name, engine='netconf')
        oc_sock = self.get_file(name, engine='openconfig')
        snmp_sock = self.get_file(name, engine='snmp')
        syslog_sock = self.get_file(name, engine='syslog')
        template = convert_template(TEMPLATE, fabric_name=self.fabric,
                                    role=role, n_pifs=n_pifs,
                                    n_leafs=self.n_leafs,
                                    n_spines=self.n_spines,
                                    n_bleafs=self.n_border_leafs or 0,
                                    n_super_spines=self.n_super_spines or 0,
                                    netconf_socket=nsock,
                                    oc_socket=oc_sock,
                                    snmp_socket=snmp_sock,
                                    syslog_socket=syslog_sock,
                                    collector=self.collector or '',
                                    snmp_oids=snmp_oids,
                                    sflows_filename=sflows_filename)
        with open(self.get_file(name, ftype='conf'), 'w') as fd:
            fd.write(template)

    def launch_container(self, name, role, n_pifs,
                         environment=ENV_SIMULATOR):
        label = {'fabric': self.fabric, 'role': role}
        try:
            absname = os.path.join(CONFDIR, name)
            os.mkdir(absname)
        except OSError:
            pass
        self.create_template(name, role, n_pifs)
        if name not in self.containers:
            ip = next(self.free_ips)
            docker_h.create_container(self.network, ip, name, label, environment)

    def post(self, fabric_name, interface, subnet, gateway, collector=None,
             address_pool=None, n_leafs=0, n_spines=0,
             n_super_spines=0, n_border_leafs=0, n_pifs=48):
        """ Create a fabric with the simulated spine and leaf servers """
        self.fabric = fabric_name
        self.network = '-'.join([self.fabric, 'Network'])
        network_detail = docker_h.get_network(self.network)
        if network_detail:
            return self.put(fabric_name, n_leafs, n_spines, n_border_leafs,
                            n_super_spines, n_pifs, address_pool, collector)
        self.n_spines = n_spines
        self.n_leafs = n_leafs
        self.n_border_leafs = n_border_leafs
        self.n_super_spines = n_super_spines
        self.n_pifs = n_pifs
        self.collector = collector
        self.containers = dict()
        if address_pool and type(address_pool) is not list:
            address_pool = ast.literal_eval(address_pool)
        docker_h.create_network(self.network, interface=interface,
                                subnet=subnet, gw=gateway)
        self.free_ips = iter(get_available_ips(subnet, gateway, address_pool))
        try:
            self.launch_containers()
        except:
            self.delete(self.fabric)
            raise
        return self.get(self.fabric)

    def put(self, fabric_name, n_leafs=0, n_spines=0, n_border_leafs=0,
            n_super_spines=0, n_pifs=48, address_pool=None, collector=None):
        """ Update the number of leafs and spines in an existing fabric """
        self.fabric = fabric_name
        self.n_spines = n_spines
        self.n_border_leafs = n_border_leafs
        self.n_super_spines = n_super_spines
        self.n_leafs = n_leafs
        self.n_pifs = n_pifs
        self.collector = collector
        if address_pool and type(address_pool) is not list:
            address_pool = ast.literal_eval(address_pool)
        self.containers = docker_h.list_containers(self.fabric)
        self.network = '-'.join([self.fabric, 'Network'])
        network_detail = docker_h.get_network(self.network)
        if not network_detail:
            raise InvalidUsage("Fabric %s not found"%self.fabric, 404)
        available_ips = get_available_ips(network_detail['subnet'],
            network_detail['gateway'], address_pool)
        self.free_ips = iter(available_ips - docker_h.get_assigned_ips(self.network))
        self.launch_containers()
        return self.get(self.fabric)

    def update_device(self, device_name, manager=None, secret=None, device_id=None):
        sock_file = self.get_file(device_name, 'netconf', ftype='sock')
        payload = {'manager': manager, 'secret': secret, 'device_id': device_id}
        send_event(sock_file, 'dic', payload)
