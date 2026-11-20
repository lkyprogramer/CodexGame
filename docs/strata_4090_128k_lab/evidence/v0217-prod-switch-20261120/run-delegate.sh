#!/bin/sh
# 2026-11-20: production switched to Strata v0.2.17 (lab baseline B2), tree /home/hhtele/strata-0.2.17 (see its run-iq3_xxs.sh and IDENTITY.json).
# The systemd unit still names this file (changing the unit needs root); this script only hands over.
# Rollback: cp /home/hhtele/strata-0.2.3/run-iq3_xxs.sh.pre-0217-20261120 /home/hhtele/strata-0.2.3/run-iq3_xxs.sh
exec /home/hhtele/strata-0.2.17/run-iq3_xxs.sh
