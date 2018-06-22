#!/bin/bash
#
# Collects configs and logs for the various GRR components and
# uploads them to Appveyor so they are available after the build.

set -ex

readonly INITIAL_DIR="${PWD}"

mkdir appveyor_e2e_artifacts
cd appveyor_e2e_artifacts

mkdir server-configs server-logs client-configs client-logs
sudo cp /usr/share/grr-server/install_data/etc/grr-server.yaml server-configs/ || true # Primary server config.
sudo cp /etc/grr/server.local.yaml server-configs/ || true # Server writeback.
sudo cp /usr/share/grr-server/lib/python2.7/site-packages/grr/var/log/* server-logs/ || true
sudo cp /usr/lib/grr/grr_*_amd64/grrd.yaml client-configs/ || true # Primary client config.
sudo cp /etc/grr.local.yaml client-configs/ || true # Secondary client config.
sudo cp /var/log/GRRlog.txt client-logs/ || true

# Give read permissions to the non-root user.
sudo chown -R "$(whoami):$(whoami)" server-configs server-logs client-configs client-logs

cd "${INITIAL_DIR}"

# Artifact paths must be relative to the root of the GRR repo.
appveyor PushArtifact e2e.log -DeploymentName 'Test Output'

for cfg in appveyor_e2e_artifacts/server-configs/*; do
  appveyor PushArtifact "${cfg}" -DeploymentName 'Server Configs'
done

for log in appveyor_e2e_artifacts/server-logs/*; do
  appveyor PushArtifact "${log}" -DeploymentName 'Server Logs'
done

for cfg in appveyor_e2e_artifacts/client-configs/*; do
  appveyor PushArtifact "${cfg}" -DeploymentName 'Client Configs'
done

for log in appveyor_e2e_artifacts/client-logs/*; do
  appveyor PushArtifact "${log}" -DeploymentName 'Client Logs'
done
