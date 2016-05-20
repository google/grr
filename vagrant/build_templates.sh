#!/bin/bash

set -e

function usage() {
  echo "Usage: ./build_templates.sh [vagrant box name]"
  exit
}

if [ $# -ne 1 ]; then
  usage
fi

export SSH_AUTH_SOCK=""
vagrant up "$1"
vagrant ssh -c "source ~/grrbuild/PYTHON_ENV/bin/activate && grr_client_build build --output /grr/executables/" "$1"

# Centos and ubuntu build the same components, so just build once.
if [ "$1" == "ubuntu_lucid32" ] || [ "$1" == "ubuntu_lucid64" ] || [ "$1" == "OS_X_10.8.5" ]; then
  vagrant ssh -c "source ~/grrbuild/PYTHON_ENV/bin/activate && grr_client_build build_components --output /grr/executables/components" "$1"
fi

if [ $? -eq 0 ]; then
  vagrant halt "$1"
fi
