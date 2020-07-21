import ast
from flask import jsonify
from collections import defaultdict
from common.docker_api import docker_h
from netaddr import IPNetwork, IPAddress
from common.util import get_available_ips, convert_template, \
                        GeventLib, delete_file
from common.exceptions import InvalidUsage
import os

CONFDIR = '/etc/simulator'
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

    def create_template(self, name, role, n_peers, n_pifs):
        sflows_filename = os.path.join(CONFDIR, name+'.sflows')
        template = convert_template(TEMPLATE, fabric_name=self.fabric,
                                    role=role, n_peers=n_peers, n_pifs=n_pifs,
                                    collector=self.collector or '',
                                    sflows_filename=sflows_filename)
        with open(os.path.join(CONFDIR, name+'.conf'), 'w') as fd:
            fd.write(template)

    def post(self, fabric_name, interface, subnet, gateway, collector=None,
             address_pool=None, n_leafs=None, n_spines=None,
             n_border_leafs=None, n_pifs=48):
        """ Create a fabric with the simulated spine and leaf servers """
        self.fabric = fabric_name
        self.n_spines = n_spines
        self.n_leafs = n_leafs
        self.n_border_leafs = n_border_leafs or 0
        self.n_pifs = n_pifs
        self.collector = collector
        self.containers = dict()
        if address_pool and type(address_pool) is not list:
            address_pool = ast.literal_eval(address_pool)
        self.network = '-'.join([self.fabric, 'Network'])
        docker_h.create_network(self.network, interface=interface,
                                subnet=subnet, gw=gateway)
        self.free_ips = iter(get_available_ips(subnet, gateway, address_pool))
        try:
            self.launch_containers()
        except:
            self.delete(self.fabric)
            raise
        return self.get(self.fabric)

    @classmethod
    def delete(self, fabric_name):
        """ Delete the corresponding fabric """
        self.containers = docker_h.list_containers(fabric_name,
                               all=True)
        GeventLib(10).map(self._delete, list(self.containers.keys()))
        network = '-'.join([fabric_name, 'Network'])
        docker_h.delete_network(network)

    def _delete(self, name):
        docker_h.delete_container(self.containers[name]['id'])
        sflows_filename = os.path.join(CONFDIR, name+'.sflows')
        config_filename = os.path.join(CONFDIR, name+'.conf')
        delete_file(sflows_filename)
        delete_file(config_filename)
 
    def launch_containers(self):
        for index in range(self.n_spines):
            name = '-'.join([self.fabric, 'Spine%s'%index])
            peers = self.n_leafs + self.n_border_leafs
            pifs = peers + self.n_pifs
            self.launch_container(name, 'spine', peers, pifs)

        for index in range(self.n_leafs):
            name = '-'.join([self.fabric, 'Leaf%s'%index])
            self.launch_container(name, 'leaf', self.n_spines, self.n_pifs)

        for index in range(self.n_border_leafs):
            name = '-'.join([self.fabric, 'BLeaf%s'%index])
            self.launch_container(name, 'bleaf', self.n_spines, self.n_pifs)

    def launch_container(self, name, role, n_peers, n_pifs,
                         environment=ENV_SIMULATOR):
        label = {'fabric': self.fabric, 'role': role}
        self.create_template(name, role, n_peers, n_pifs)
        if name in self.containers:
            if role == 'spine':
                docker_h.restart_container(self.containers[name]['id'])
        else:
            ip = next(self.free_ips)
            docker_h.create_container(self.network, ip, name, label, environment)

    def put(self, fabric_name, n_leafs=None, n_spines=None, n_border_leafs=None,
            n_pifs=48, address_pool=None, collector=None):
        """ Update the number of leafs and spines in an existing fabric """
        self.fabric = fabric_name
        self.n_spines = n_spines
        self.n_border_leafs = n_border_leafs or 0
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
