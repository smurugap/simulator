from common.rest_api import RestServer

class SimulatorAgentApi(RestServer):
    def __init__(self, server='127.0.0.1'):
        super(SimulatorAgentApi, self).__init__(server, 8989)

    def create_fabric(self, fabric_name, interface, subnet, gateway,
                          address_pool=None, n_leafs=None, n_spines=None,
                          n_border_leafs=None, n_pifs=None, collector=None):
        addr_ranges = [(x['start'], x['end']) for x in address_pool or []]
        payload = {'interface': interface,
                   'subnet': subnet,
                   'gateway': gateway,
                   'address_pool': addr_ranges,
                   'n_leafs': n_leafs,
                   'n_spines': n_spines,
                   'n_border_leafs': n_border_leafs,
                   'n_pifs': n_pifs,
                   'collector': collector}
        return self.post('fabric/'+fabric_name, payload, timeout=600)

    def delete_fabric(self, fabric_name):
        return self.delete('fabric/'+fabric_name, timeout=1800)

    def update_fabric(self, fabric_name, address_pool=None, n_leafs=None,
                      n_spines=None, n_border_leafs=None, n_pifs=None,
                      collector=None):
        addr_ranges = [(x['start'], x['end']) for x in address_pool or []]
        payload = {'address_pool': addr_ranges,
                   'n_leafs': n_leafs,
                   'n_spines': n_spines,
                   'n_pifs': n_pifs,
                   'n_border_leafs': n_border_leafs,
                   'collector': collector}
        return self.put('fabric/'+fabric_name, payload)

    def get_fabric(self, fabric_name):
        return self.get('fabric/'+fabric_name)['fabrics'].get(fabric_name)

    def check_and_create_fabric(self, fabric_name, interface, subnet, gateway,
                                **kwargs):
        if self.get_fabric(fabric_name):
            return self.update_fabric(fabric_name, **kwargs)
        return self.create_fabric(fabric_name, interface, subnet,
                                  gateway, **kwargs) 

    def start_sflows(self, fabric_name, direction,
                     n_bms_per_router, n_flows):
        payload = {'action': 'start',
                   'direction': direction,
                   'n_flows': n_flows,
                   'bms_per_router': n_bms_per_router}
        return self.post('sflow/'+fabric_name, payload)

    def stop_sflows(self, fabric_name):
        return self.post('sflow/'+fabric_name, {'action': 'stop'})
