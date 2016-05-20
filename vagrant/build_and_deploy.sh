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
  # We expect templates to be built and available in
  # grr/executables/windows/templates
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
  vagrant ssh -c "source ~/PYTHON_ENV/bin/activate && grr_client_build build  --output /grr/grr/executables/" "$1"
  vagrant ssh -c "source ~/PYTHON_ENV/bin/activate && grr_client_build build_components  --output /grr/grr/executables/components" "$1"
  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
  cd ../../
  # Repack templates into executables and sign
  if [ "$1" == "centos_5.11_64" ]; then
    ARCH=amd64
  elif [ "$1" == "centos_5.11_32" ]; then
    ARCH=i386
  fi;

  grr_client_build --platform linux --arch $ARCH --package_format rpm --sign buildanddeploy --templatedir grr/executables/linux/templates
  cd -

else
  vagrant up "$1"
  vagrant ssh -c "source ~/PYTHON_ENV/bin/activate && grr_client_build buildanddeploy" "$1"
  if [ $? -eq 0 ]; then
    vagrant halt "$1"
  fi
fi
