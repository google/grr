#!/bin/bash
set -e
while [[ ! -f grr_client.deb ]]
do
    wget -O grr_client.deb "${linux_installer_download_url}"  || rm -f grr_client.deb
    sleep 10
done
apt install -y ./grr_client.deb
