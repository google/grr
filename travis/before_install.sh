#!/bin/bash
set -e

sudo apt-get install python-software-properties
# No pytsk3 for precise in stable ppa
sudo add-apt-repository ppa:gift/dev -y
sudo apt-get update -q

sudo apt-get install -y \
  git-core \
  libdistorm64-dev \
  libdistorm64-1 \
  libfreetype6-dev \
  libpng-dev \
  libprotobuf-dev \
  ncurses-dev \
  protobuf-compiler \
  python-dev \
  python-m2crypto \
  python-pip \
  python-protobuf \
  python-support \
  pytsk3 \
  sleuthkit \
  swig

sudo -H pip install pip --upgrade

# A more recent version of distribute is required for matplotlib (to be
# installed in the next step) on vanilla precise. So you will need to uncomment
# this for testing. However, travis has upgraded their version of
# setuptools so this isn't required. And running it actually breaks travis. It
# seems to trigger this bug which was supposedly fixed as of pip 6.1.0:
# https://github.com/pypa/pip/issues/2438
#
# sudo -H pip install distribute --upgrade

