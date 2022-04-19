#!/bin/bash
#
# Installs the 64-bit client deb in the GRR server's virtualenv
# and runs end-to-end tests against it. If the tests fail, the script
# will terminate with a non-zero exit-code.
#
# Needs to be run as root.

set -ex

readonly FLAKY_TESTS_ARR=(\
  TestCheckRunner.runTest \
)
# Convert array to string (comma-separated).
readonly FLAKY_TESTS="$(IFS=,;echo "${FLAKY_TESTS_ARR[*]}")"

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

# USER_PROCESS utmp records don't seem to get created in Appveyor VMs during
# builds (they do get created however when you ssh to the VM). GRR, as well as
# system utilities like 'who' and 'users' rely on those records to determine
# which users are logged into a machine. Since there are a number of end-to-end
# tests that rely on the presence of user profiles in the knowledge-base, we
# generate a dummy wtmp entry for the 'appveyor' user, which is the role used
# for running tests. This is obviously a hack.
useradd -m appveyor
echo "[7] [01234] [ts/3] [appveyor] [pts/3       ] [100.100.10.10       ] [100.100.10.10  ] [Thu Jan 01 00:00:00 1970 UTC]" > wtmp.txt
utmpdump /var/log/wtmp >> wtmp.txt
utmpdump --reverse < wtmp.txt > /var/log/wtmp
utmpdump /var/log/wtmp

apt install -y /usr/share/grr-server/executables/installers/grr_*_amd64.deb

CLIENT_ID="$(grr_console --code_to_execute 'from grr_response_test import test_utils; print(test_utils.GetClientId("/etc/grr.local.yaml"))')"

echo "Installed GRR client [Id ${CLIENT_ID}]"

# Enable verbose logging and increase polling frequency so flows
# get picked up quicker.
echo -e "Logging.engines: stderr,file\nLogging.verbose: True\nClient.poll_max: 5" >> /etc/grr.local.yaml

systemctl restart grr

grr_end_to_end_tests --verbose \
  --api_password "${GRR_ADMIN_PASS}" \
  --client_id "${CLIENT_ID}" \
  --flow_timeout_secs 240 \
  --flow_results_sla_secs 60 \
  --skip_tests "${FLAKY_TESTS}" \
  2>&1 | tee e2e.log

if [[ ! -z "$(cat e2e.log | grep -F '[ FAIL ]')" ]]; then
  fatal 'End-to-end tests failed.'
fi

if [[ -z "$(cat e2e.log | grep -F '[ PASS ]')" ]]; then
  fatal "Expected to find at least one passing test in the test log. It is possible no tests actually ran."
fi
