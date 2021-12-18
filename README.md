# Brief background on Simulator:
http://ez/simulator

# PreRequisite:
* x86 server reachable from controller via fabric network

# Installation:
* [Install docker](https://docs.docker.com/engine/install/centos/) on the test server
* docker pull the simulator agent container
```sh
$ docker pull smurugap/simulator:latest
```
* Launch the simulator agent container
```sh
$ echo 4096 > /proc/sys/fs/inotify/max_user_instances
$ sysctl -w net.ipv4.ip_forward=1
$ service firewalld stop
$ iptables -P FORWARD ACCEPT
$ mkdir -p /etc/simulator
$ docker run -itd --privileged -v /var/run:/var/run -v /etc/simulator:/etc/simulator --net host --name simulator-agent smurugap/simulator:latest
```

# Scale Test Execution:
## Create fabric yaml:
* Login to the container and update the [fabric.yaml](https://github.com/smurugap/simulator/blob/master/fabric.yaml) file

## Resource Monitoring (optional):
* Launch resource monitoring service (glances) on controllers (Appformix, Contrail, JFM, JFM-Edge etal)
```sh
$ docker run -d --restart="always" -p 61208-61209:61208-61209 -e GLANCES_OPT="-w" -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host nicolargo/glances
```

## Onboard devices:
```sh
$ python fabric.py -i fabric.yaml -o stage1
```
* Create simulators (-o create_simulators)
* Brownfield onboard the fabric (-o onboard_fabric)
* Assign roles based on ip-clos type (-o assign_roles)

## Deleting Simulators:
```sh
$ python fabric.py -i fabric.yaml -o delete_simulators
```

## Create workloads:
```sh
python fabric.py -i fabric.yaml -o stage2 -t 5
```
* Create Virtual Networks
* Create Virtual Port Groups
* Create Vlans in the VPGs
Note: -t controls the no of parallel threads

## Create L3 gateway:
```sh
python fabric.py -i fabric.yaml -o stage3 -t 5
```
* Create Logical Routers and link the VNs
* Extend the logical routers to respective physical routers

## Create services:
```sh
python fabric.py -i fabric.yaml -o stage4 -t 6
```
* Create Security Groups and attach to VPGs
* Create Storm Control Profiles + Port Profiles and attach to VPGs

## Create Unmanaged Instances:
```sh
python fabric.py -i fabric.yaml -o stage5 -t 3
```
* Create Routed VN, Routed VPG and LogicalRouter with Routed VN properties

## Create all overlay objects:
Wrapper around all the stages
```sh
python fabric.py -i fabric.yaml -o create -t 5
```

## Deleting overlay objects:
```sh
python fabric.py -i fabric.yaml -o delete -t 6
```

## Deleting fabric:
```sh
python fabric.py -i fabric.yaml -o delete_fabric
```

## Generate sflows:
To generate 1000 sampled flows with new flows every 10 minutes under test-fabric fabric
```sh
python fabric.py -i fabric.yaml -o start_sflows -c n_flows=1000,fabric=test-fabric,refresh_interval=10
```

## Stop sflows:
To stop generating sampled flows
```sh
python fabric.py -i fabric.yaml -o stop_sflows -c fabric=test-fabric
```
