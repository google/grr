#!/bin/bash
#
# This script is run when the client is started in the Docker Compose stack.
# It installs the provided debian package if no installers or fleetspeak-client
# binary are found.
# The client installers are repacked by the admin ui.
INSTALLERS_DIR="/client_installers"

find ${INSTALLERS_DIR}

if ! command -v fleetspeak-client &> /dev/null
    then
        echo "**Installing Client from debian package."
        dpkg -i  ${INSTALLERS_DIR}/*.deb
    else
        echo "** Found fleetspeak-client binary, skipping install."
fi

echo "** Completed client setup."
