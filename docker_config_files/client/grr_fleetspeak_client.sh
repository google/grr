#!/bin/bash
if [ -f /usr/share/grr-server/bin/grr_fleetspeak_client ]; then
  /usr/share/grr-server/bin/python /usr/share/grr-server/bin/grr_fleetspeak_client "$@"
else
  /usr/sbin/grrd "$@"
fi
