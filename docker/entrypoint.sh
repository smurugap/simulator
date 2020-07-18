#!/bin/bash
set -x
if [ "$MODE" = "simulator" ]; then
    python /opt/simulator/simulator.py
else
    python /opt/simulator/simulator_agent.py
fi
exec $@
