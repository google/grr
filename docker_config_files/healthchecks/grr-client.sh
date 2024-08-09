#!/bin/bash
#
# Health check for the grr-client Container in the Docker Compose stack.
# As soon as the grr client process is running the service is considered
# healthy.

set -ex

if [[ "$(ps aux | grep grrd | grep -v grep | wc -l)" == "0" ]] && 
   [[ "$(ps aux | grep '/usr/share/grr-server/bin/grr_fleetspeak_client' | grep -v grep | wc -l)" == "0" ]]
then
    echo "Healthckeck: GRR client process not running"
    exit 1
fi
