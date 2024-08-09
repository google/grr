#!/bin/bash
#
# This script is run when Fleetspeak runs the GRR client.
# It first checks whether we run Docker Compose Watch (i.e. in dev mode).
#   If so we run the grr_fleetspeak_client python script so Docker Compose can
#   swap in the source code updates on a continuous basis.
#   If not we run grrd as we would do so in production.
if [ -f /usr/share/grr-server/bin/grr_fleetspeak_client ]; then
  /usr/share/grr-server/bin/python /usr/share/grr-server/bin/grr_fleetspeak_client "$@"
else
  /usr/sbin/grrd "$@"
fi
