#!/bin/bash
#
# Health check for the grr-admin-ui Container in the Docker Compose stack.
# As soon a debian file has been written to the /client_installer we
# assume the service is healthy and the client container can be started.

set -ex

if [[ -z "$(find /client_installers -name '*.deb')" ]]; then
        echo "Healthcheck: GRR client installer not available"
        exit 1
fi

