#!/bin/bash
#
# Script for testing travis configuration. Use with 'vagrant up travis_testing'.
#
set -e

sudo apt-get install -y python-pip

# Move to the directory this script is in, then step one directory up.
cd /grr
travis/before_install.sh
travis/install.sh
./run_tests.sh
