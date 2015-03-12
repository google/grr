#!/bin/bash

function usage() {
  echo "Usage: ./build_and_deploy.sh [vagrant box name]"
  exit
}


if [ $# -ne 1 ]; then
  usage
fi

export SSH_AUTH_SOCK=""
vagrant up $1
vagrant ssh -c "cd / && source ~/PYTHON_ENV/bin/activate && PYTHONPATH=. python grr/client/client_build.py --config=grr/config/grr-server.yaml buildanddeploy" $1
