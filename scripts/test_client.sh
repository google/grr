#!/bin/bash
PREFIX=/usr
CONFIG=$PREFIX/share/grr/executables/linux/installers/grr.ini
TMP_CONFIG=/tmp/$(basename $CONFIG) 

if [ ! -f $CONFIG ]; then
  echo "No linux config found at $CONFIG. Did you run build_clients.sh?"
fi

echo "Copying $CONFIG to /tmp"
cp -f ${CONFIG} ${TMP_CONFIG}

CMD="python2 $PREFIX/lib/pymodules/python2.7/grr/client/client.py \
--location=http://localhost:8080/control \
--poll_max=5 \
--foreman_check_frequency=20 \
--verbose \
--client_config=${TMP_CONFIG} \
$@"

echo "Running:"
echo $CMD
echo

$CMD
