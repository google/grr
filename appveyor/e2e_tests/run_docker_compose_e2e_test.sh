#!/bin/bash
#
# Runs the e2e tests in the Docker Compose stack.
#
# This script is executed in the grr Docker container or in an
# environment with the grr src and develpment environment
# (grr-python-api, grr-test) available. And assumes the
# Docker Compose stack to be running with exposed ports for
# the admin API and GRR database.
#
# Running this test (from the main folder):
# - Start the Docker Compose stack with:
#     $ docker compose up
#
# - Build and run the GRR Docker container and set the entrypoint
#   to this script:
#     $ docker build -f ./Dockerfile . -t local-grr-container
#     $ docker run \
#        --add-host=host.docker.internal:host-gateway \
#        -v $(pwd):/github_workspace \
#        -w /github_workspace \
#        --entrypoint appveyor/e2e_tests/run_docker_compose_e2e_test.sh  \
#        local-grr-container \
#        (docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' grr-client)

set -ex

# The IP address of the client inside the Docker Compose stack.
readonly CLIENT_IP=${1}

readonly GRR_API="http://host.docker.internal:8000"

readonly SKIP_TESTS_ARR=(\
  TestCheckRunner.runTest \
  # TODO: TSK pathtype is not working on Linux clients, skip tests.
  TestListDirectoryTSKLinux.runTest \
  TestTransferLinux.testMultiGetFileTSK \
  TestRawFilesystemAccessUsesTskOnNonWindows.runTest \
)
# Convert array to string (comma-separated).
SKIP_TESTS="$(IFS=,;echo "${SKIP_TESTS_ARR[*]}")"
readonly SKIP_TESTS

readonly GRR_ADMIN_USER=test-user
readonly GRR_ADMIN_PASS=test-password

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

# Install the grr tests
pip install -e grr/test

grr_config_updater add_user ${GRR_ADMIN_USER} \
    --password ${GRR_ADMIN_PASS} \
    --secondary_configs docker_config_files/testing/grr.testing.yaml

grr_end_to_end_tests --verbose \
  --secondary_configs docker_config_files/testing/grr.testing.yaml \
  --api_endpoint "http://host.docker.internal:8000" \
  --api_user "${GRR_ADMIN_USER}" \
  --api_password "${GRR_ADMIN_PASS}" \
  --client_ip "${CLIENT_IP}" \
  --flow_timeout_secs 240 \
  --flow_results_sla_secs 60 \
  --skip_tests "${SKIP_TESTS}" \
  2>&1 | tee e2e.log

if [[ ! -z "$(cat e2e.log | grep -F '[ FAIL ]')" ]]; then
  fatal 'End-to-end tests failed.'
fi

if [[ -z "$(cat e2e.log | grep -F '[ PASS ]')" ]]; then
  fatal "Expected to find at least one passing test in the test log. It is possible no tests actually ran."
fi
