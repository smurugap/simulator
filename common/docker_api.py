import docker
import subprocess
import re
from docker.types import LogConfig, IPAMConfig, IPAMPool
from common.util import get_prouter_index

class DockerInterface(object):
    def __init__(self):
        self._client = docker.from_env()
        if hasattr(self._client, 'api'):
            self._client = self._client.api

    @property
    def my_id(self):
        if not getattr(self, '_id', None):
            cmd = "cat /proc/self/cgroup | grep name"
            output = subprocess.Popen(cmd, shell=True,
                stdout=subprocess.PIPE).communicate()[0].strip()
            self._id = output.split('/')[-1]
        return self._id

    @property
    def my_details(self):
        if not getattr(self, '_details', None):
            self._details = self._client.inspect_container(self.my_id)
        return self._details

    @property
    def my_hostname(self):
        return self.my_details['Name'].strip('/')

    def _get_ip_from_instance(self, instance_details):
        for key, value in instance_details['NetworkSettings']['Networks'].items():
            return value['IPAddress']

    @property
    def my_ip(self):
        return self._get_ip_from_instance(self.my_details)

    @property
    def my_index(self):
        return get_prouter_index(self.my_hostname)

    @property
    def my_image(self):
        return self.my_details['Config']['Image']

    def get_network_id(self, network_name):
        for net in self._client.networks():
            if net['Name'] == network_name:
                return net['Id']

    def get_assigned_ips(self, network):
        assigned_ips = set()
        network_id = self.get_network_id(network)
        if not network_id:
            return list()
        net_details = self._client.inspect_network(network_id)
        for key, value in net_details['Containers'].items():
            assigned_ips.add(str(value['IPv4Address'].split('/')[0]))
        return assigned_ips

    def restart_container(self, container_id):
        self._client.restart(container_id)

    def create_container(self, network, ip, name, labels=None,
                         environment=None):
        lc = LogConfig(type=LogConfig.types.JSON, config={'max-size': '1g'})
        hc = self._client.create_host_config(binds=['/var/run:/var/run:rw',
            '/etc/simulator:/etc/simulator:rw'], log_config=lc)
        nc = self._client.create_networking_config({
            network: self._client.create_endpoint_config(ipv4_address=ip)})
        container = self._client.create_container(self.my_image,
            host_config=hc, name=name, tty=True, hostname=name, detach=True,
            networking_config=nc, labels=labels, environment=environment)
        self._client.start(container=container.get('Id'))
        return container.get('Id')

    def list_containers(self, fabric_name=None, all=False):
        filters = dict()
        if fabric_name:
            filters['label'] = 'fabric=%s'%(fabric_name)
        containers = dict()
        for entry in self._client.containers(filters=filters, all=all):
            containers[entry['Names'][0].strip("/")] = {
                'id': entry['Id'],
                'fabric': entry['Labels'].get('fabric'),
                'role': entry['Labels'].get('role'),
                'address': self._get_ip_from_instance(entry)}
        return containers

    def delete_container(self, container_id):
        self._client.stop(container=container_id)
        self._client.remove_container(container=container_id)

    def create_network(self, name, interface, subnet, gw, labels=None):
        options = {'parent': interface}
        ipam_pool = IPAMPool(subnet=subnet, gateway=gw)
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])
        return self._client.create_network(name, driver='macvlan',
                options=options, ipam=ipam_config,labels=labels)

    def delete_network(self, name):
        try:
            return self._client.remove_network(name)
        except:
            pass

    def get_network(self, name):
        network_id = self.get_network_id(name)
        if not network_id:
            return dict()
        network = self._client.inspect_network(network_id)
        subnet = network['IPAM']['Config'][0]['Subnet']
        gateway = network['IPAM']['Config'][0]['Gateway']
        return {'subnet': subnet, 'gateway': gateway}

docker_h = DockerInterface()

if __name__ == "__main__":
    client = DockerInterface()
    client.list_containers()
    '''
    net=client.create_network('pvt-net', 'enp3s0f1', '192.1.1.0/24','192.1.1.254')
    id=client.create_container(network='pvt-net',ip='192.1.1.10',name='test-simulator-pvt')
    ips = client.get_assigned_ips('pvt-net')
    print ips
    client.delete_container(id)
    client.delete_network('pvt-net')
    '''
    print(client.my_image)
    client.list_containers(all=True)
