#!/bin/bash
#
# Fetches the latest server deb from Google Cloud Storage and installs it.
# This script needs root privileges to run.

set -ex

readonly CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
readonly INITIAL_DIR="${PWD}"
readonly DEB_TEMPDIR=/tmp/grr_deb_install

if [[ -e "${DEB_TEMPDIR}" ]]; then
  rm -rf "${DEB_TEMPDIR}"
fi

mkdir "${DEB_TEMPDIR}"
cd "${DEB_TEMPDIR}"

# Install Google Cloud SDK if not installed.
if [[ -z "$(type gsutil 2>/dev/null)" ]]; then
  echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
  apt update && apt install -y google-cloud-sdk
fi

gsutil cp gs://autobuilds.grr-response.com/_latest_server_deb/* .
echo -e ".changes file for downloaded server deb:\n\n$(cat grr-server_*_amd64.changes)\n"
DEBIAN_FRONTEND=noninteractive apt install -y ./grr-server_*_amd64.deb
grr_config_updater initialize --noprompt --external_hostname=localhost --admin_password="${GRR_ADMIN_PASS}"
echo 'Logging.verbose: True' >> /etc/grr/server.local.yaml
systemctl restart grr-server

echo "Installation of server deb completed."

tar xzf grr-server_*.tar.gz
source /usr/share/grr-server/bin/activate
pip install --no-index --find-links=grr/local_pypi grr/local_pypi/grr-response-test-*.zip
deactivate

cd "${INITIAL_DIR}"
