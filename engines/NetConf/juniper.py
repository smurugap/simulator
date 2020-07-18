import gevent
from gevent import monkey
monkey.patch_all()
from plugin import NetconfPluginBase
import os
from lxml import etree

MYDIR = os.path.dirname(os.path.abspath(__file__))

SYSINFO = '/tmp/system_info'
TEMPLATES = {'version': 'version.j2',
             'system_info': 'system_info.j2',
             'chassis_mac': 'chassis_mac.j2',
             'interfaces': 'interfaces.j2',
             'config_interfaces': 'config_interfaces.j2',
             'hardware_inventory': 'hardware_inventory.j2',
             'commit_info': 'commit_info.j2',
             'lldp_info': 'lldp_info.j2',
            }

def get_templates_abs_path():
    return {k: os.path.join(MYDIR, v) for k,v in TEMPLATES.items()}

class NetconfPlugin(NetconfPluginBase):
    def __init__(self, *args, **kwargs):
        super(NetconfPlugin, self).__init__(*args, **kwargs)
        self.templates = get_templates_abs_path()
        self.update_system_info()

    def update_system_info(self):
        content = self._convert_template('system_info', rtype='raw',
            version=self.version, model=self.model, hostname=self.hostname)
        with open(SYSINFO, 'w+') as fd:
            fd.write(content)

    def rpc_get_configuration(self, session, rpc, *args, **kwargs):
        rpc = rpc.xpath('./get-configuration')[0]
        is_diff = rpc.get('compare') == 'rollback'
        if is_diff:
            reply = etree.Element('configuration-information')
            reply.append(etree.Element('configuration-output'))
            return reply
        is_committed = rpc.get('database') == 'committed'
        is_interfaces = rpc.xpath('./configuration/interfaces')
        is_roptions = rpc.xpath('./configuration/routing-options')
        if is_committed:
          if is_interfaces:
            return self._convert_template('config_interfaces',
                                                 lo0_ip=self.tunnel_ip)
          elif is_roptions:
            reply = '<configuration>\n<routing-options>\n<static>\n<route>\n'+\
                '<name>0.0.0.0/0</name>\n<next-hop>10.87.101.13</next-hop>\n'+\
                '</route>\n</static>\n</routing-options>\n</configuration>'
            return etree.fromstring(reply)

    def rpc_get_interface_information(self, *args, **kwargs):
        return self._convert_template('interfaces',
            count=self.n_interfaces, lo_ip=self.tunnel_ip)

    def rpc_command(self, session, rpc):
        command = rpc.xpath('./command')[0].text
        filename = None
        if 'show chassis hardware' in command:
            return self._convert_template('hardware_inventory',
                hostname=self.hostname, model=self.model)
        elif 'show interfaces' in command:
            return self.rpc_get_interface_information()
        elif 'show chassis mac-addresses' in command:
            return self._convert_template('chassis_mac',
                macaddr=self.macaddr)
        elif 'show system commit' in command:
            return self._convert_template('commit_info', count=10)
        elif 'show version' in command:
            return self._convert_template('version', model=self.model,
                hostname=self.hostname, version=self.version)
        elif 'lldp' in command:
            return self._convert_template('lldp_info', my_index=self.my_index,
                peer_prefix=self.peer_prefix or 'dummy', n_peers=self.n_peers)

class SSHPlugin(object):
    def check_channel_exec_request(self, channel, command):
        self.queue.put('disable', False)
        if "show system information" in command:
            command = "cat %s"%SYSINFO
        process = gevent.subprocess.Popen(command, stdout=gevent.subprocess.PIPE,
                                          stdin=gevent.subprocess.PIPE,
                                          stderr=gevent.subprocess.PIPE,
                                          shell=True)
        gevent.spawn(self._read_response, channel, process)
        gevent.sleep(0)
        return True

    def _read_response(self, channel, process):
        gevent.sleep(0)
        for line in process.stdout:
            channel.send(line)
        process.communicate()
        channel.send_exit_status(process.returncode)
        # Let clients consume output from channel before closing
        gevent.sleep(.1)
        channel.close()
        gevent.sleep(0)
