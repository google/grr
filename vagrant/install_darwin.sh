#!/bin/bash

set -e

# Update the system
function system_update() {
  sudo softwareupdate --install --all
}

# Install homebrew
function install_homebrew() {
  # Use /dev/null as stdin to disable prompting during install
  ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" </dev/null
  brew doctor
  brew update
  brew install makedepend
}

# Install our python dependencies into a virtualenv that uses the new python
# version
function install_python_deps() {
  sudo -H pip install --upgrade pip
  sudo -H pip install --upgrade virtualenv

  # Required for M2Crypto. Broken on swig 3.0.5:
  # https://github.com/M2Crypto/M2Crypto/issues/24
  brew tap homebrew/versions
  brew install homebrew/versions/swig304

  virtualenv -p /usr/local/bin/python2.7 PYTHON_ENV
  source PYTHON_ENV/bin/activate
  pip install -r /grr/requirements.txt
}

# Install patched m2crypto, hopefully this patch will eventually be accepted so
# we don't have to do this and can just add a line to requirements.txt
# https://github.com/M2Crypto/M2Crypto/pull/16
function install_m2crypto() {
  wget --quiet https://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-0.22.3.tar.gz#md5=573f21aaac7d5c9549798e72ffcefedd
  wget --quiet https://googledrive.com/host/0B1wsLqFoT7i2aW5mWXNDX1NtTnc/m2crypto-0.22.3-fixes.patch
  tar zxf M2Crypto-0.22.3.tar.gz
  cd M2Crypto-0.22.3
  patch -u -p1 < ../m2crypto-0.22.3-fixes.patch
  python setup.py build
  python setup.py install
  cd -
}

function install_sleuthkit() {
  wget --quiet -O sleuthkit-3.2.3.tar.gz https://sourceforge.net/projects/sleuthkit/files/sleuthkit/3.2.3/sleuthkit-3.2.3.tar.gz/download
  tar zxf sleuthkit-3.2.3.tar.gz
  cd sleuthkit-3.2.3
  ./configure
  make -j4
  sudo make install
  cd -
}

function install_pytsk() {
  brew install talloc
  wget --quiet https://github.com/py4n6/pytsk/releases/download/20150111/pytsk-20150111.tgz
  tar zxf pytsk-20150111.tgz
  cd pytsk
  python setup.py build
  python setup.py install
  cd -
}

# We want to run unprivileged since that's what homebrew expects, but vagrant
# provisioning runs as root.
case $EUID in
  0)
    sudo -u vagrant -i $0  # script calling itself as the vagrant user
    ;;
  *)
    system_update
    install_homebrew
    brew install wget
    brew install python
    brew install protobuf
    install_python_deps
    install_m2crypto
    install_sleuthkit
    install_pytsk
    ;;
esac
