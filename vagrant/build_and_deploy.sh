#!/bin/bash

set -e

function usage() {
  echo "Usage: ./build_and_deploy.sh [vagrant box name]"
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
  # Check osssigncode is installed and bail early if not.
  echo "Checking for osslsigncode, required to sign windows executables."
  which osslsigncode
  if [ $? -ne 0 ]; then
    echo "Missing osslsigncode, required to sign windows executables."
    exit 1
  fi
  # First, build the templates on windows. See Vagrantfile for info on why we
  # use --provision. These templates don't go into a timestamped directory
  # because the next step runs on linux and needs to know where to find them.
  vagrant reload --provision windows_7_64
  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
  cd ../../
  # Repack templates into executables and sign
  PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml --platform windows --sign buildanddeploy --templatedir grr/executables/windows/templates
  cd -

elif [ "$1" == "centos_5.11_64" ] || [ "$1" == "centos_5.11_32" ]; then
  # Treat RPMs differently because we want to sign them.

  which rpmsign
  if [ $? -ne 0 ]; then
    echo "Missing rpmsign, required to sign RPMs."
    exit 1
  fi

  vagrant up "$1"
  vagrant ssh -c "cd /grr/ && PROTO_SRC_ROOT=$PROTO_SRC_INSTALLED make && cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml build" "$1"
  vagrant ssh -c "cd /grr/ && PROTO_SRC_ROOT=$PROTO_SRC_INSTALLED make && cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml build_components" "$1"
  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
  cd ../../
  # Repack templates into executables and sign
  PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml --platform linux --package_format rpm --sign buildanddeploy --templatedir grr/executables/linux/templates
  cd -

else
  vagrant up "$1"
  # We need to compile the protos inside the build environment because the host
  # may not have the correct proto compiler.
  vagrant ssh -c "cd /grr/ && PROTO_SRC_ROOT=$PROTO_SRC_INSTALLED make && cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml buildanddeploy" "$1"
  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
fi
