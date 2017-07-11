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
vagrant ssh -c "bash /grr/vagrant/install_grr.sh && source ~/grrbuild/PYTHON_ENV/bin/activate && grr_client_build build --output /grr/executables/" "$1"

if [ $? -eq 0 ]; then
  vagrant halt "$1"
fi
