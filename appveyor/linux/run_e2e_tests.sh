#!/bin/bash
#
# Installs the 64-bit client deb in the GRR server's virtualenv
# and runs end-to-end tests against it. If the tests fail, the script
# will terminate with a non-zero exit-code.
#
# Needs to be run as root.

set -ex

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

apt install -y /usr/share/grr-server/executables/installers/grr_*_amd64.deb

CLIENT_ID="$(grr_console --code_to_execute 'from grr.test_lib import test_lib; print(test_lib.GetClientId("/etc/grr.local.yaml"))')"

echo "Installed GRR client [Id ${CLIENT_ID}]"

# Enable verbose logging and increase polling frequency so flows
# get picked up quicker.
echo -e "Logging.engines: stderr,file\nLogging.verbose: True\nClient.poll_max: 5" >> /etc/grr.local.yaml

systemctl restart grr

grr_end_to_end_tests --api_password "${GRR_ADMIN_PASS}" --client_id "${CLIENT_ID}" --flow_timeout_secs 60 --verbose 2>&1 | tee e2e.log

if [[ ! -z "$(cat e2e.log | grep -F '[ FAIL ]')" ]]; then
  fatal 'End-to-end tests failed.'
fi

if [[ -z "$(cat e2e.log | grep -F '[ PASS ]')" ]]; then
  fatal "Expected to find at least one passing test in the test log. It is possible no tests actually ran."
fi
