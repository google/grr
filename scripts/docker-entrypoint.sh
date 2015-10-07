#!/bin/bash

# Entrypoint script for docker demo server. This script handles initializing the
# server, setting configuration and kicking off the services.

set -e

if [ "$1" = 'grr' ]; then
  if [ ! -e "/etc/grr/server.local.yaml" ]; then
    if [ $EXTERNAL_HOSTNAME ] && [ $ADMIN_PASSWORD ]; then
      grr_config_updater initialize --noprompt --external_hostname="$EXTERNAL_HOSTNAME" --admin_password="$ADMIN_PASSWORD"
    else
      echo "initialize hasn't run and EXTERNAL_HOSTNAME/ADMIN_PASSWORD not set"
      exit 1
    fi
  fi

  # Handle installation via dpkg or setup.py
  DAEMON="/usr/bin/grr_server"
  [ -x "${DAEMON}" ] || DAEMON="/usr/local/bin/grr_server"

  # Running multiple components like this is less than ideal. Replace with
  # individual docker components that point to a http datastore.
  echo "Admin UI gui is at http://${EXTERNAL_HOSTNAME}:8000, clients will poll to http://${EXTERNAL_HOSTNAME}:8080"
  ${DAEMON} --start_http_server --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml &
  ${DAEMON} --start_ui --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml &
  ${DAEMON} --start_worker --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml &
  ${DAEMON} --start_worker --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml &
  ${DAEMON} --start_worker --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml &
  ${DAEMON} --start_worker --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml
else
  exec "$@"
fi

