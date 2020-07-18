#! /bin/bash
mkdir -p /etc/simulator
name=${2:-simulator-agent}
image=${1:-smurugap/simulator:latest}
docker run -itd --privileged -v /var/run:/var/run -v /etc/simulator:/etc/simulator --net host --name $name $image
