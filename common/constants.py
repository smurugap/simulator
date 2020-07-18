USERNAME='root'
PASSWORD='Embe1mpls'
DEFAULT_PIFS = 48
DEFAULT_CLOS_TYPE = 'erb'
DEFAULT_OVERLAY_ASN = 64512
VALID_OVERLAY_ROLES = ['dc-gateway', 'crb-access', 'dci-gateway',
                       'ar-client', 'crb-gateway', 'erb-ucast-gateway',
                       'crb-mcast-gateway', 'ar-replicator', 'route-reflector']
DEFAULT_OVERLAY_SUBNET_MASK = 28
SFLOW_OVERLAY_IP_PROTOCOLS = ['TCP', 'UDP', 'ICMP']
SAMPLES_PER_PKT = 6

class Events(object):
    START_SFLOW = 'start_sflow'
    STOP_SFLOW = 'stop_sflow'
