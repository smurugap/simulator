# Brief background on Simulator:
https://docs.google.com/document/d/1yxiU9xpD49ZHLAMtnuzOHnYOm4ZOa89pLYqYNH9dIPY

# PreRequisite:
* x86 server reachable from controller via fabric network

# Installation:
* [Install docker](https://docs.docker.com/engine/install/centos/) on the test server
* docker pull the simulator agent container
```sh
docker pull smurugap/simulator:0.2b
```
* Launch the simulator agent container
```sh
mkdir -p /etc/simulator
docker run -itd --privileged -v /var/run:/var/run -v /etc/simulator:/etc/simulator --net host --name simulator-agent smurugap/simulator:0.2b
```

# Execution:
## Create fabric yaml:
* Login to the container and update the [fabric.yaml](https://github.com/smurugap/simulator/blob/master/fabric.yaml) file

## Onboard devices:
`python scale.py -i fabric.yaml -o stage1`
* Create simulators (-o create_simulators)
* Brownfield onboard the fabric (-o onboard_fabric)
* Assign roles based on ip-clos type (-o assign_roles)

## Deleting Simulators:
`python scale.py -t fabric.yaml -o delete_simulators`

## Create workloads:
`python scale.py -t fabric.yaml -o stage2`
* Create Virtual Networks
* Create Virtual Port Groups
* Create Vlans in the VPGs

## Create L3 gateway:
`python scale.py -t fabric.yaml -o stage3`
* Create Logical Routers and link the VNs
* Extend the logical routers to respective physical routers

## Create services:
`python scale.py -t fabric.yaml -o stage4`
* Create Security Groups and attach to VPGs
* Create Storm Control Profiles + Port Profiles and attach to VPGs

## Create Unmanaged Instances:
`python scale.py -t fabric.yaml -o stage5`
* Create Routed VN, Routed VPG and LogicalRouter with Routed VN properties

## Deleting overlay objects:
`python scale.py -t fabric.yaml -o delete`

## Deleting fabric:
`python scale.py -t fabric.yaml -o delete_fabric`

## Generate sflows:
Note: Restart the docker container after creating simulators to workaround the iproute2 bug
`python fabric.py -i fabric.yaml -o start_sflows -c n_flows=1000,fabric=test-fabric,refresh_interval=10`

## Stop sflows:
`python fabric.py -i fabric.yaml -o stop_sflows -c fabric=test-fabric`
