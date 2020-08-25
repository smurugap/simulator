#! /bin/bash
set -x
echo 1024 > /proc/sys/fs/inotify/max_user_instances
service firewalld stop
iptables -P FORWARD ACCEPT
sysctl -w net.ipv4.ip_forward=1
name=${2:-simulator-agent}
image=${1:-smurugap/simulator:latest}
mkdir -p /etc/simulator
docker run -itd --privileged -v /var/run:/var/run -v /etc/simulator:/etc/simulator --net host --name $name $image
