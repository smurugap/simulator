import gevent
from plugin import NetconfPluginBase
import os
from lxml import etree
import time
import uuid

MYDIR = os.path.dirname(os.path.abspath(__file__))

SYSINFO = '/tmp/system_info'
TEMPLATES = {'version': 'version.j2',
             'system_info': 'system_info.j2',
             'chassis_mac': 'chassis_mac.j2',
             'chassis_fan': 'chassis_fan.j2',
             'interfaces': 'interfaces.j2',
             'config_interfaces': 'config_interfaces.j2',
             'hardware_inventory': 'rpc_get_chassis_inventory',
             'commit_info': 'commit_info.j2',
             'lldp_info': 'lldp_info.j2',
             'chassis_alarms': 'chassis_alarms.j2',
             'config_set': 'config_set.j2',
             'config_xml': 'config_xml.j2',
             'config_ascii': 'config_ascii.j2',
             'interface_ri_juniper_private1': 'interface_ri_juniper_private1.j2'
            }

def get_templates_abs_path():
    return {k: os.path.join(MYDIR, 'templates', v) for k,v in TEMPLATES.items()}

class NetconfPlugin(NetconfPluginBase):
    def __init__(self, *args, **kwargs):
        super(NetconfPlugin, self).__init__(*args, **kwargs)
        self.templates = get_templates_abs_path()
        self.update_system_info()
        self.chassis_alarms = dict()
        self.interfaces = dict()
        self.commit_revision = 1000
        self.commit_timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        self.commit_id = str(uuid.uuid4())

    def update_system_info(self):
        content = self._convert_template('system_info', rtype='raw')
        with open(SYSINFO, 'w+') as fd:
            fd.write(content)

    def rpc_get_configuration(self, session, rpc, *args, **kwargs):
        rpc = rpc.getchildren()[0]
        is_diff = rpc.get('compare') == 'rollback'
        if is_diff:
            reply = etree.Element('configuration-information')
            reply.append(etree.Element('configuration-output'))
            return reply
        output_format = rpc.get('format')
        if output_format == 'set':
            return self._convert_template('config_set')
        elif output_format == 'ascii':
            return self._convert_template('config_ascii')
        is_committed = rpc.get('database') == 'committed'
        is_interfaces = rpc.xpath('./configuration/interfaces')
        is_roptions = rpc.xpath('./configuration/routing-options')
        if is_committed:
          if is_interfaces:
            return self._convert_template('config_interfaces')
          elif is_roptions:
            reply = '<configuration>\n<routing-options>\n<static>\n<route>\n'+\
                '<name>0.0.0.0/0</name>\n<next-hop>10.87.101.13</next-hop>\n'+\
                '</route>\n</static>\n</routing-options>\n</configuration>'
            return etree.fromstring(reply)
        return self._convert_template('config_xml')

    def rpc_command(self, session, rpc):
        command = rpc.xpath('./command')[0].text
        filename = None
        kwargs = dict()
        rformat = rpc.getchildren()[0].get('format')
        if rformat == 'json':
            kwargs['rtype'] = 'json'
        if 'show chassis hardware' in command:
            template = 'hardware_inventory'
        elif 'show interfaces' in command:
            template = 'interfaces'
        elif 'show chassis mac-addresses' in command:
            template = 'chassis_mac'
        elif 'show system commit' in command:
            template = 'commit_info'
        elif 'show version' in command:
            template = 'version'
        elif 'lldp' in command:
            template = 'lldp_info'
        elif 'show chassis fan' in command:
            template = 'chassis_fan'
        else:
            print 'ToDo: command is ', command
            raise Exception('command is %s'%command)
        return self._convert_template(template, **kwargs)

    def rpc_file_show(self, session, rpc, *args, **kwargs):
        FILES_DIR=os.path.join(MYDIR, 'files')
        fullfilename = rpc.xpath('./file-show/filename')[0].text
        filename = os.path.basename(fullfilename)
        if filename in os.listdir(FILES_DIR):
            with open(os.path.join(FILES_DIR, filename)) as fd:
                content = fd.read()
            reply_str = '<file-content encoding="text" ' +\
                'filename="%s" filesize="%s">'%(filename, len(content)) +\
                content + "</file-content>"
            reply = etree.fromstring(reply_str)
        else:
            print 'ToDo: rpc_file_show ', etree.tostring(rpc), args, kwargs
            reply = None
        return reply

    def rpc_get_interface_information(self, session, rpc, *args, **kwargs):
        ri = rpc.xpath('./routing-instance')
        kwargs = dict()
        rformat = rpc.getchildren()[0].get('format')
        if rformat == 'json':
            kwargs['rtype'] = 'json'
        if ri:
            if "__juniper_private1__" in ri[0].text:
                return self._convert_template('interface_ri_juniper_private1')
        return self._convert_template('interfaces')

class SSHPlugin(object):
    def check_channel_exec_request(self, channel, command):
        self.queue.put('disable', False)
        if "show system information" in command:
            command = "cat %s"%SYSINFO
        print 'ToDo: SSH command', command
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
