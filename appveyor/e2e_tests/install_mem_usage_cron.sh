#!/bin/bash
#
# Enables periodic logging of memory usage in an Appveyor VM.

set -ex

# Write header row of log file.
echo "$(date) $(free -hmw | grep available)" >> /var/log/grr_e2e_mem_usage.log
# Install the crontab file.
cp "${APPVEYOR_BUILD_FOLDER}/appveyor/e2e_tests/grr_e2e_mem_usage" /etc/cron.d/
systemctl restart cron
