#!/bin/bash
#
# Installs the server deb from a local path.
# This script needs root privileges to run.

set -ex

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

# TODO: make Fleetspeak create its own db, if necessary.
mysql -u root --password=root -e "CREATE USER 'runner'@'localhost' IDENTIFIED BY 'password'; GRANT ALL PRIVILEGES on grr.* to runner@'localhost'; GRANT ALL PRIVILEGES on fleetspeak.* to runner@'localhost'; CREATE DATABASE fleetspeak"

grr_config_updater initialize --noprompt --external_hostname=localhost --admin_password=e2e_tests --mysql_username=runner --mysql_password=password --mysql_host=localhost --mysql_db=grr --mysql_fleetspeak_db=fleetspeak --use_fleetspeak
echo 'Logging.verbose: True' >> /etc/grr/server.local.yaml
mkdir -p /var/log/grr
echo 'Logging.path: /var/log/grr' >> /etc/grr/server.local.yaml
systemctl restart grr-server

echo "Installation of server deb completed."

tar xzf "$GITHUB_WORKSPACE"/_artifacts/grr-server_*.tar.gz
source /usr/share/grr-server/bin/activate
pip install --no-index --find-links=grr/local_pypi grr/local_pypi/grr-response-test-*.zip
deactivate

cd "${INITIAL_DIR}"
