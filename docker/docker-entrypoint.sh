#!/bin/bash

# Entrypoint script for GRR docker components.
# If specific components aren't specified this script will initialize the GRR
# server and run all components inside the same container.

set -e

run_component() {
  COMPONENT=$1; shift
  grr_server --component "${COMPONENT}" "$@"
}

initialize() {
  if [[ ! -e "${VIRTUALENV}/install_data/etc/server.local.yaml" ]]; then
    if [[ "${EXTERNAL_HOSTNAME}" ]] && [[ "${ADMIN_PASSWORD}" ]]; then
      grr_config_updater initialize \
        --noprompt \
        --use_rel_db \
        --external_hostname="${EXTERNAL_HOSTNAME}" \
        --admin_password="${ADMIN_PASSWORD}" \
        --mysql_hostname="${GRR_MYSQL_HOSTNAME}" \
        --mysql_port="${GRR_MYSQL_PORT:-0}" \
        --mysql_db="${GRR_MYSQL_DB}" \
        --mysql_username="${GRR_MYSQL_USERNAME}" \
        --mysql_password="${GRR_MYSQL_PASSWORD}"
    else
      echo "initialize hasn't run and EXTERNAL_HOSTNAME/ADMIN_PASSWORD not set"
      exit 1
    fi
  fi
}

APPLICATION=$1;
VIRTUALENV="/usr/share/grr-server/"
if [[ ${APPLICATION} = 'grr' ]]; then
  if [[ "${DISABLE_INTERNAL_MYSQL}" != 'true' ]]; then
    # Start the "inherited" mariadb:bionic entrypoint.
    # See: https://github.com/docker-library/mariadb/blob/master/10.1/Dockerfile
    gosu mysql bash -x <<EOF
    export MYSQL_ALLOW_EMPTY_PASSWORD=1
    source docker-entrypoint.sh

    mysql_check_config mysqld
    docker_setup_env mysqld
    docker_create_db_directories
    docker_verify_minimum_env
    docker_init_database_dir mysqld
    docker_temp_server_start mysqld
    docker_setup_db
    docker_process_init_files /docker-entrypoint-initdb.d/*
EOF
  fi
  source "${VIRTUALENV}/bin/activate"

  if [[ "$#" -eq 1 ]]; then
    # Run all components in the same container. This is only useful for
    # testing and very small deployments.
    initialize
    echo "Admin UI gui is at http://${EXTERNAL_HOSTNAME}:8000, clients will poll to http://${EXTERNAL_HOSTNAME}:8080"
    run_component frontend &
    run_component admin_ui &
    run_component worker &
    run_component worker &
    run_component worker &
    run_component worker
  else
    # TODO(user): this won't actually work yet. Need to solve the problem of
    # getting the initialized config to each component.
    COMPONENT=$2; shift 2
    run_component "${COMPONENT}" "$@"
  fi
else
  exec "$@"
fi
