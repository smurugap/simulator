#! /bin/bash
cat > /etc/contrail/vnc_api_lib.ini << EOF
[global]
TIMEOUT = 60
insecure = True
EOF
