FROM centos:centos7

RUN mkdir -p /opt/simulator /etc/contrail
ENV PYTHONPATH /opt/simulator

# Yum install base packages
RUN yum install -y yum-plugin-priorities
RUN yum install -y epel-release gcc python-devel git vim libffi-devel
RUN yum install -y python-pip libxml2-devel nc iproute openssh-clients net-tools
RUN pip install pip==20.1.1 setuptools==44.1.1

# pip install python packages
COPY docker/requirements.txt docker/entrypoint.sh /
RUN pip install -r requirements.txt

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

# Few patches
COPY docker/increase_vnc_api_timeout.sh docker/apply_patches.sh /
COPY patches /patches
RUN /apply_patches.sh
RUN /increase_vnc_api_timeout.sh

ENTRYPOINT ["/entrypoint.sh"]
