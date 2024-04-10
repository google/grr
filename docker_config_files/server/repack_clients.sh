#!/bin/bash

# This script repacks the client using the provided configuration
# and uploads the installers to the blobstore to make them available
# via the Web UI.
#
# In this docker compose example the folder the installers are stored
# is mounted in the grr-client container, which will install the debian
# installer on startup.
INSTALLERS_DIR="/client_installers"


if [[ -z "$(ls -A ${INSTALLERS_DIR})" ]]
    then
        echo "** Repacking clients."
        grr_config_updater repack_clients \
            --secondary_configs /configs/server/grr.server.yaml
    else
        echo "** Found existing client installers dir, skipping repacking."
fi