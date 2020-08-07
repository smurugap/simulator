import re
import os
import json
from collections import defaultdict, OrderedDict

system_rules = ['ether-type', 'allow-dns-dhcp', 'tdenyall']

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        super(CustomEncoder, self).default(obj)

class ParseConfig(object):
    def __init__(self, filename):
        self.filename = filename
        self.storm_controls = set()
        self.interfaces = defaultdict(dict)
        self.bds = defaultdict(dict)
        self.vrfs = defaultdict(dict)
        self.pifs = defaultdict(dict)
        self.firewall_filters = defaultdict(set)

    def register_storm_control(self, line):
        pattern = '.*interfaces (?P<pif>\S+) unit (?P<unit>\d+)'+\
            '.*storm-control (?P<name>\S+)'
        match = re.match(pattern, line)
        if match:
            self.storm_controls.add(match.group('name'))
            lif = match.group('pif')+'.'+match.group('unit')
            self.interfaces[lif]['storm_control'] = match.group('name')

    def register_vlan_members(self, line):
        pattern = '.*interfaces (?P<pif>\S+) unit (?P<unit>\d+)'+\
            '.*vlan members (?P<vlan>\S+)'
        match = re.match(pattern, line)
        if match:
            lif = match.group('pif')+'.'+match.group('unit')
            if 'vlans' not in self.interfaces[lif]:
                self.interfaces[lif]['vlans'] = set()
            self.interfaces[lif]['vlans'].add(match.group('vlan'))
            if 'lifs' not in self.pifs[match.group('pif')]:
                self.pifs[match.group('pif')]['lifs'] = set()
            self.pifs[match.group('pif')]['lifs'].add(lif)

    def register_address(self, line):
        pattern = '.*interfaces (?P<pif>\S+) unit (?P<unit>\d+)'+\
            '.*family inet.* address (?P<address>\S+)'
        match = re.match(pattern, line)
        if match:
            lif = match.group('pif')+'.'+match.group('unit')
            if 'address' not in self.interfaces[lif]:
                self.interfaces[lif]['vlans'] = set()
            self.interfaces[lif]['address'].add(match.group('address'))

    def register_vlan_ids(self, line):
        pattern = '.*vlans (?P<name>\S+) vlan-id (?P<id>\d+)'
        match = re.match(pattern, line)
        if match:
            self.bds[match.group('name')]['vlan'] = match.group('id')

    def register_vxlan_ids(self, line):
        pattern = '.*vlans (?P<name>\S+) vxlan vni (?P<id>\d+)'
        match = re.match(pattern, line)
        if match:
            self.bds[match.group('name')]['vxlan'] = match.group('id')

    def register_irb_in_vlan(self, line):
        pattern = '.*vlans (?P<name>\S+) l3-interface (?P<irb>\S+)'
        match = re.match(pattern, line)
        if match:
            self.bds[match.group('name')]['irb'] = match.group('irb')

    def register_vrfs(self, line):
        pattern = '.*routing-instances (?P<name>\S+) interface irb.(?P<unit>\d+)'
        match = re.match(pattern, line)
        if match:
            vrf = match.group('name')
            if 'irb' not in self.vrfs[vrf]:
                self.vrfs[vrf]['irb'] = set()
            self.vrfs[vrf]['irb'].add('irb.%s'%match.group('unit'))

    def register_ae(self, line):
        pattern = '.*interfaces (?P<pif>\S+).*802.3ad (?P<ae>\w+)'
        match = re.match(pattern, line)
        if match:
            self.pifs[match.group('pif')]['ae'] = match.group('ae')

    def register_firewall_filter(self, line):
        pattern = '.*interfaces (?P<pif>\S+) unit (?P<unit>\d+)'+\
            '.*filter input-list (?P<name>\S+)'
        match = re.match(pattern, line)
        if match:
            lif = match.group('pif')+'.'+match.group('unit')
            name = match.group('name')
            if 'denyall' in name:
                return
            if 'filters' not in self.interfaces[lif]:
                self.interfaces[lif]['filters'] = set()
            self.interfaces[lif]['filters'].add(name)

    def register_filter_rules(self, line):
        pattern = '.*firewall family.*filter (?P<name>\S+) term (?P<rule>\S+)'
        match = re.match(pattern, line)
        if match:
            rule = match.group('rule')
            if rule in system_rules:
                return
            self.firewall_filters[match.group('name')].add(rule)

    def parse(self):
        if not os.path.exists(self.filename):
            return dict()
        with open(self.filename, 'r') as fd:
            content = fd.readlines()
        for line in content:
            if 'vlan members' in line:
                self.register_vlan_members(line)
            elif 'vlan-id' in line:
                self.register_vlan_ids(line)
            elif 'vxlan vni' in line:
                self.register_vxlan_ids(line)
            elif 'l3-interface' in line:
                self.register_irb_in_vlan(line)
            elif re.search('routing-instances.*interface', line):
                self.register_vrfs(line)
            elif '802.3ad' in line:
                self.register_ae(line)
#            elif 'address' in line:
#                self.register_address(line)
            elif "firewall family" in line:
                self.register_filter_rules(line)
            elif "filter input-list" in line:
                self.register_firewall_filter(line)
            elif 'storm-control' in line:
                self.register_storm_control(line)
        return self.summarize()

    def summarize(self):
        interfaces = 0; rules = 0
        for name, details in self.interfaces.items():
            interfaces += len(details['vlans'])
        for name, details in self.firewall_filters.items():
            rules += len(details)
        output = {
            'vlans': len(self.bds),
            'vlan_details': self.bds,
            'interfaces': interfaces,
            'interface_details': self.interfaces,
            'pifs': len(self.pifs),
            'pif_details': self.pifs,
            'filters': len(self.firewall_filters),
            'filter_details': self.firewall_filters,
            'rules': rules,
            'vrfs': len(self.vrfs),
            'vrf_details': self.vrfs,
            'storm_controls': len(self.storm_controls),
            'storm_control_details': self.storm_controls
        }
        return json.dumps(output, indent=4, cls=CustomEncoder)

def main():
    obj = ParseConfig('current.config')
    print obj.parse()

if __name__ == "__main__":
    main()
