#! /bin/bash
# Apply netconf patch
cd /usr/lib/python2.7/site-packages/netconf
git apply /patches/netconf.patch.1

# Apply spyne patch
cd /usr/lib/python2.7/site-packages/spyne
git apply /patches/spyne.patch.1

# Apply exabgp patch
