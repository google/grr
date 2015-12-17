#!/bin/bash

# Entrypoint script for GRR docker components.
# If specific components aren't specified this script will initialize the GRR
# server and run all components inside the same container.

set -e

run_component() {
  COMPONENT=$1; shift
  ${DAEMON} --start_${COMPONENT} --disallow_missing_config_definitions --config=/etc/grr/grr-server.yaml "$@"
}

initialize() {
  if [ ! -e "/etc/grr/server.local.yaml" ]; then
    if [ $EXTERNAL_HOSTNAME ] && [ $ADMIN_PASSWORD ]; then
      grr_config_updater initialize --noprompt --external_hostname="$EXTERNAL_HOSTNAME" --admin_password="$ADMIN_PASSWORD"
    else
      echo "initialize hasn't run and EXTERNAL_HOSTNAME/ADMIN_PASSWORD not set"
      exit 1
    fi
  fi
}

APPLICATION=$1;
if [ ${APPLICATION} = 'grr' ]; then
  DAEMON="/usr/bin/grr_server"
  [ -x "${DAEMON}" ] || DAEMON="/usr/local/bin/grr_server"

  if [ "$#" -eq 1 ]; then
    # Run all components in the same container. This is only useful for
    # testing and very small deployments.
    initialize
    echo "Admin UI gui is at http://${EXTERNAL_HOSTNAME}:8000, clients will poll to http://${EXTERNAL_HOSTNAME}:8080"
    run_component http_server &
    run_component ui &
    run_component worker &
    run_component worker &
    run_component worker &
    run_component worker
  else
    # TODO(user): this won't actually work yet. Need to solve the problem of
    # getting the initialized config to each component.
    COMPONENT=$2; shift 2
    run_component ${COMPONENT} "$@"
  fi
else
  exec "$@"
fi

