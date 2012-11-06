#!/bin/bash

CONFIG=/etc/grr/grr-server.conf

# If server is running we stop it as we can't bind to
# port 8000 otherwise.
sudo initctl status grr-single-server | grep "running"
IS_RUNNING=$?
if [ $IS_RUNNING = 0 ]; then
  echo "Stopping currently running UI"
  sudo initctl stop grr-single-server
fi

grr_server.py \
--start_ui \
--verbose \
--config=$CONFIG \
--django_debug \
$@
