FROM centos:7.7.1908

RUN mkdir -p /opt/simulator /etc/contrail
ENV PYTHONPATH /opt/simulator:/opt/simulator/engines

# Yum install base packages
RUN yum install -y yum-plugin-priorities && \
    yum install -y epel-release gcc python-devel && \
    yum install -y python-pip libxml2-devel nc iproute \
                   openssh-clients vim net-tools

# pip install python packages
COPY docker/requirements.txt docker/entrypoint.sh docker/increase_vnc_api_timeout.sh /
RUN pip install -r requirements.txt
RUN ./increase_vnc_api_timeout.sh

# Add 
WORKDIR /opt/simulator
ADD simulator.py simulator_agent.py fabric.py fabric.yaml ./
COPY scripts /opt/simulator/scripts
COPY engines /opt/simulator/engines
COPY common /opt/simulator/common
COPY agent /opt/simulator/agent

# Untar VncAPI and ExaBGP packages
COPY docker/vnc_api.tgz docker/exabgp.tgz /
RUN tar -xzf /vnc_api.tgz
RUN tar -xzf /exabgp.tgz

ENTRYPOINT ["/entrypoint.sh"]
