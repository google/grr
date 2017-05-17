#!/bin/bash

# Docker image doesn't have some basics
apt-get update
apt-get install -y wget sudo

wget --no-check-certificate https://raw.githubusercontent.com/google/grr/master/scripts/install_script_ubuntu.sh

# We don't want to initialize because that has interactive prompts. Instead we craft config below.
sed -i '/run_cmd_confirm grr_config_updater initialize/d' ./install_script_ubuntu.sh

/bin/bash ./install_script_ubuntu.sh -y

service grr-single-server stop

# edit these to your liking
echo "AdminUI.url: http://0.0.0.0:8000" >> /etc/grr/server.local.yaml
echo "Monitoring.alert_email: grr-monitoring@example.com" >> /etc/grr/server.local.yaml
echo "Monitoring.emergency_access_email: grr-emergency@example.com" >> /etc/grr/server.local.yaml
echo "Client.control_urls: http://0.0.0.0:8080/control" >> /etc/grr/server.local.yaml
echo "Logging.domain: example.com" >> /etc/grr/server.local.yaml
echo "ClientBuilder.executables_path: /usr/share/grr/executables" >> /etc/grr/server.local.yaml
echo "Client.name: grr-client" >> /etc/grr/server.local.yaml


grr_config_updater generate_keys
grr_config_updater repack_clients
grr_config_updater update_user --password s3cur3password admin
grr_config_updater load_memory_drivers

#service grr-single-server start
