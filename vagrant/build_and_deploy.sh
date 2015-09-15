#!/bin/bash

set -e

function usage() {
  echo "Usage: ./build_and_deploy.sh [vagrant box name]"
  exit
}


if [ $# -ne 1 ]; then
  usage
fi

export SSH_AUTH_SOCK=""
if [ $1 == "windows_7_64" ]; then
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
    vagrant halt $1
  fi
  cd ../../
  PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml --platform windows --sign buildanddeploy --templatedir grr/executables/windows/templates
  cd -
else
  vagrant up $1
  # We need to compile the protos inside the build environment because the host
  # may not have the correct proto compiler.
  vagrant ssh -c "cd /grr/proto/ && make && cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml buildanddeploy" $1
  if [ $? -eq 0 ]; then
    vagrant halt $1
  fi
fi
