#!/bin/bash
#
# Script to change from running as grr-single-server to running the components
# Individually.
#

SWITCHDIR=$1;

MULTI_SERVICES="grr-http-server grr-ui grr-enroller grr-worker"
SINGLE_SERVICES="grr-single-server"

if [ "$SWITCHDIR" = "" ] || [ "$SWITCHDIR" = "multi" ]; then
  ENABLE=${MULTI_SERVICES}
  DISABLE=${SINGLE_SERVICES}
elif [ "$SWITCHDIR" = "single" ]; then
  ENABLE=${SINGLE_SERVICES}
  DISABLE=${MULTI_SERVICES}
else
  echo "Specify multi or single"
  exit 1;
fi

for SVC in ${DISABLE}; do
  echo "Disabling ${SVC}"
  sudo service ${SVC} stop;
  sudo sed -i 's/START=\"yes\"/START=\"no\"/' "/etc/default/${SVC}";
done

for SVC in ${ENABLE}; do
  echo "Enabling ${SVC}"
  sudo sed -i 's/START=\"no\"/START=\"yes\"/' "/etc/default/${SVC}";
  sudo service ${SVC} start;
done

