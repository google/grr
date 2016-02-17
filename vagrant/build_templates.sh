#!/bin/bash

set -e

function usage() {
  echo "Usage: ./build_templates.sh [vagrant box name]"
  exit
}

if [ $# -ne 1 ]; then
  usage
fi

export PROTO_SRC_INSTALLED="/grrbuild/"
if [ "$1" == "OS_X_10.8.5" ]; then
  # Protobuf library installed by homebrew on OS X
  export PROTO_SRC_INSTALLED="/usr/local/Cellar/protobuf/2.6.1/include/"
fi

export SSH_AUTH_SOCK=""
if [ "$1" == "windows_7_64" ]; then
  # Build the templates on windows by running --provision.
  vagrant reload --provision windows_7_64
  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
else
  vagrant up "$1"
  # We need to compile the protos inside the build environment because the host
  # may not have the correct proto compiler.
  vagrant ssh -c "cd /grr/ && PROTO_SRC_ROOT=$PROTO_SRC_INSTALLED make && cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml build" "$1"
  vagrant ssh -c "cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml build_component /grr/client/components/chipsec_support/setup.py /grr/" "$1"

  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
fi
