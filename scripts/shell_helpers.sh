#!/bin/bash
# Some basic functions to help with enabling and disabling GRR services.

GRR_SERVICES="grr-http-server grr-ui grr-worker"

alias grr_stop_all='stop_services "$GRR_SERVICES"'
alias grr_start_all='start_services "$GRR_SERVICES"'
alias grr_enable_all='enable_services "$GRR_SERVICES"'
alias grr_restart_all='grr_stop_all; grr_start_all'

function stop_services()
{
  local SERVICES;
  SERVICES=$1;
  for SERVICE in ${SERVICES}
  do
    if [ -x $(which service) ]; then
      sudo service ${SERVICE} status | grep "running"
        IS_RUNNING=$?
        if [ $IS_RUNNING = 0 ]; then
          echo "Stopping ${SERVICE}"
          sudo service ${SERVICE} stop;
        fi
    else
      echo "Systems that don't use 'service' not supported"
      exit 1
    fi
  done
}


function start_services()
{
  local SERVICES;
  SERVICES=$1;
  for SERVICE in ${SERVICES}
  do
    if [ -x $(which initctl) ]; then
      sudo service ${SERVICE} status | grep "stop"
        IS_RUNNING=$?
        if [ $IS_RUNNING = 0 ]; then
          echo "Starting ${SERVICE}"
          sudo service ${SERVICE} start;
        fi
    else
      echo "Systems that don't use 'service' not supported"
      exit 1
    fi
  done
}

function enable_services()
{
  local SERVICES;
  SERVICES=$1;
  for SERVICE in ${SERVICES}
  do
    SERVICE_DEFAULT=/etc/default/${SERVICE}
    sed -i 's/START=\"no\"/START=\"yes\"/' ${SERVICE_DEFAULT};

    echo "Starting ${SERVICE}"

    initctl status ${SERVICE} | grep "running"
    IS_RUNNING=$?
    if [ $IS_RUNNING = 0 ]; then
      service ${SERVICE} stop
    fi
    service ${SERVICE} start
  done
}
