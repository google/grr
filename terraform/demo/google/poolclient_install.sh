#!/bin/bash
set -e
while [[ ! -f grr_client.deb ]]
do
    wget -O grr_client.deb "${linux_installer_download_url}"  || rm -f grr_client.deb
    sleep 10
done
apt install -y ./grr_client.deb

GRR_DIR_NAME=$(ls /usr/lib/grr)

mkdir -p /tmp/writebacks
mkdir -p /tmp/transaction_logs
for ((i=0; i<${num_clients}; i++))
do
  /usr/lib/grr/$${GRR_DIR_NAME}/grrd \
    --config /usr/lib/grr/$${GRR_DIR_NAME}/grrd.yaml \
    -p Config.writeback=/tmp/writebacks/$${i}.yaml \
    -p Client.transaction_log_file=/tmp/transaction_logs/$${i}.log &
done
