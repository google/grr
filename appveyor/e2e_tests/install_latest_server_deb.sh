#!/bin/bash
#
# Installs the server deb from a local path.
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

pyscript="
import configparser
config = configparser.ConfigParser()
config.read('${APPVEYOR_BUILD_FOLDER}/version.ini')
print('%s.%s.%s-%s' % (
    config.get('Version', 'major'),
    config.get('Version', 'minor'),
    config.get('Version', 'revision'),
    config.get('Version', 'release')))
"
echo -e ".changes file for server deb:\n\n$(cat "$GITHUB_WORKSPACE"/_artifacts/grr-server_*_amd64.changes)\n"
DEBIAN_FRONTEND=noninteractive apt install -y "$GITHUB_WORKSPACE"/_artifacts/grr-server_*_amd64.deb
grr_config_updater initialize --noprompt --use_rel_db --external_hostname=localhost --admin_password="${GRR_ADMIN_PASS}" --mysql_password="${APPVEYOR_MYSQL_PASS}"
echo 'Logging.verbose: True' >> /etc/grr/server.local.yaml
systemctl restart grr-server

echo "Installation of server deb completed."

tar xzf "$GITHUB_WORKSPACE"/_artifacts/grr-server_*.tar.gz
source /usr/share/grr-server/bin/activate
pip install --no-index --find-links=grr/local_pypi grr/local_pypi/grr-response-test-*.zip
deactivate

cd "${INITIAL_DIR}"
