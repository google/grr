#! /bin/bash

# GRR client docker compose initialization script.
# This script is run when the client is started in the
# docker-compose stack. It repacks the client using the
# provided configuration files and installs the resulting
# debian package if no installers or fleetspeak-client
# binary are found.
#
# This script assumes the client-config files 
# (docker_config_files/client) to be mounted at /configs.

# Template dir is initializes when building the image via
# the github actions, which also builds the templates.
TEMPLATE_DIR="/client_templates"
INSTALLERS_DIR="/client_installers"


if [[ -z "$(ls -A ${INSTALLERS_DIR})" ]]
    then
        echo "** Repacking clients."
        grr_client_build repack_multiple \
            --templates ${TEMPLATE_DIR}/*/*.zip \
            --repack_configs /configs/grr.client.yaml \
            --output_dir ${INSTALLERS_DIR}
    else
        echo "** Found existing client installers dir, skipping repacking."
fi

if ! command -v fleetspeak-client &> /dev/null
    then
        echo "**Installing Client from debian package."
        dpkg -i  ${INSTALLERS_DIR}/grr.client/*.deb
    else
        echo "** Found fleetspeak-client binary, skipping install."
fi

echo "** Completed client setup."
