from gevent import pool
from collections import MutableMapping
from netaddr import IPNetwork, IPAddress
from jinja2 import Template
from datetime import datetime
from lxml import etree
import gevent
import re
import pyinotify
import socket
import struct
import random
import time
import os
import hashlib
import hmac
import sys
CONFDIR = '/etc/simulator'

def watcher(filename, callback):
    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm)
    wm.add_watch(filename, pyinotify.IN_MODIFY)
    try:
        gevent.spawn(notifier.loop, callback=callback)
    except pyinotify.NotifierError, err:
        pass
    return notifier

def delete_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

def register_event(event, events, callback):
    events[event] = callback

def get_prouter_index(prouter):
    return int(re.findall("\d+", prouter.split("-")[-1])[0])

def get_random_mac():
    return ':'.join(map(lambda x: "%02x" % x, [0x00, 0x16, 0x3E,
        random.randint(0x00, 0x7F), random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF)]))

def get_available_ips(cidr, gateway, address_pool=None):
    ips = set()
    network = IPNetwork(cidr)
    for pool in address_pool or []:
        start, end = pool
        for ip in range(IPAddress(start), IPAddress(end) + 1):
            if ip in network:
                ips.add(str(IPAddress(ip)))
    if not address_pool:
        ips = set([str(ip) for ip in network])
    ips.discard(gateway)
    ips.discard(str(network.broadcast))
    ips.discard(str(network.network))
    return ips

def convert_template(filename, rtype='raw', **kwargs):
    with open(filename, 'r') as fd:
        template = Template(fd.read())
    content = template.render(**kwargs)
    if rtype.lower() == 'xml':
        return etree.fromstring(content.strip())
    elif rtype.lower() == 'raw':
        return content

def touch(filename):
    with open(filename, 'a'):
        pass

def time_taken(f):
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        msg = 'Time taken for op %s'%f.__name__
        tenant = None
        ret = f(*args, **kwargs)
        end_time = datetime.now()
        print msg, str(end_time - start_time), '--- current time', str(end_time)
        return ret
    return wrapper

def retry(tries=5, delay=3):
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            result = f(*args, **kwargs)
            rv = result
            while mtries > 0 and rv is not True:
                mtries -= 1
                time.sleep(mdelay)
                rv = f(*args, **kwargs)
            if not rv:
                return False
            else:
                return True
        return f_retry
    return deco_retry

def get_an_ip(cidr, offset):
    return str(IPNetwork(cidr)[offset])

def get_random_ip(cidr=None):
    if not cidr:
        cidr = get_random_cidr()
    first = IPNetwork(cidr).first
    last = IPNetwork(cidr).last
    return get_an_ip(cidr, offset=random.randint(1, last - first - 1))

def is_valid_address(address):
    ''' Validate whether the address provided is routable unicast address '''
    addr = IPAddress(address)
    if addr.is_loopback() or addr.is_reserved() or addr.is_private()\
       or addr.is_link_local() or addr.is_multicast():
        return False
    return True

alloc_addr_list = list()
def get_random_cidr(mask=28):
    ''' Generate random non-overlapping cidr '''
    global alloc_addr_list
    address = socket.inet_ntop(socket.AF_INET,
                               struct.pack('>I',
                               random.randint(2**24, 2**32 - 2**29 - 1)))
    addr = str(IPNetwork(address+'/'+str(mask)).network)
    if not is_valid_address(address) or addr in alloc_addr_list:
        cidr = get_random_cidr()
    else:
        alloc_addr_list.append(addr)
        cidr = addr+'/'+str(mask)
    return cidr

def elem2dict(node, alist=False):
    d = list() if alist else dict()
    for e in node.iterchildren():
        #key = e.tag.split('}')[1] if '}' in e.tag else e.tag
        if e.tag == 'list':
            value = elem2dict(e, alist=True)
        else:
            value = e.text if e.text else elem2dict(e)
        if type(d) == type(list()):
            d.append(value)
        else:
            d[e.tag] = value
    return d

def nc_elem2dict(node, root=False):
    d = dict()
    for e in node.iterchildren():
        if e.text:
            if e.text and e.getchildren():
                value = nc_elem2dict(e)
            else:
                value = {'data': e.text.strip()}
        else:
            value = nc_elem2dict(e)
        if e.tag in d:
            d[e.tag].append(value)
        else:
            d[e.tag] = [value]
    if root:
        d = {node.tag: [d]}
    return d

def get_file(device, engine=None, ftype='sock'):
    if ftype == 'sock':
        name = engine+'.sock'
    elif ftype == 'sflows':
        name = device+'.flows'
    elif ftype == 'oids':
        name = 'snmp.oids'
    elif ftype == 'conf':
        name = device+'.conf'
    else:
        raise Exception('Unsupported file type')
    return os.path.join(CONFDIR, device, name)

def get_sha1(secret, message):
    message = bytes(message).encode('utf-8')
    secret = bytes(secret).encode('utf-8')
    return hmac.new(secret, message, hashlib.sha1).hexdigest()

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class SafeList(list):
    def get(self, index, default=None):
        try:
            return super(SafeList, self).__getitem__(index)
        except IndexError:
            return default

class GeventLib(object):
    def __init__(self, pool_size=10):
        self.pool = pool.Pool(pool_size)

    def spawn(self, fn, entries):
        threads = list()
        for entry in entries:
            instance = SafeList(entry)
            args = instance.get(0, set())
            kwargs = instance.get(1, dict())
            threads.append(self.pool.spawn(fn, *args, **kwargs))
        gevent.joinall(threads)
        return [x.value for x in threads]

    def map(self, fn, args):
        return self.pool.map(fn, args)

class custom_dict(MutableMapping, dict):
    def __init__(self, callback):
        self.callback = callback

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            self[key] = self.callback(key)
            return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

    def __contains__(self, key):
        return dict.__contains__(self, key)

def daemonize(pid_file, log_file, fn):
    try:
        pid = os.fork()
        if pid > 0:
            return pid
#            pid = os.fork()
#            if pid == 0:
            # Exit first parent
#            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
#    os.chdir("/")
    os.setsid()
    os.umask(0)
#    sys.stdout = open(log_file, 'a+')
#    sys.stderr = open(log_file, 'a+')
    try:
        pid = os.fork()
        if pid > 0:
            with open(pid_file, 'w') as f:
                f.write('%s\n'%pid)
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
#    si = file(stdin, 'r')
#    os.dup2(si.fileno(), sys.stdin.fileno())
    fn()
