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
  # Brew doctor complains that you are using an old version of OS X.
  brew doctor || true
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
  # Required for M2Crypto in requirements.txt
  export SWIG_FEATURES="-I/usr/include/x86_64-linux-gnu"
  pip install -r /grr/client/linux/requirements.txt

  # pyinstaller fails to include protobuf because there is no __init__.py:
  # https://github.com/google/protobuf/issues/713
  touch PYTHON_ENV/lib/python2.7/site-packages/google/__init__.py
}

function install_sleuthkit() {
  wget --quiet -O sleuthkit-4.1.3.tar.gz https://sourceforge.net/projects/sleuthkit/files/sleuthkit/4.1.3/sleuthkit-4.1.3.tar.gz/download
  # Segfault fix: https://github.com/py4n6/pytsk/wiki/Building-SleuthKit
  wget --quiet https://googledrive.com/host/0B3fBvzttpiiScUxsUm54cG02RDA/tsk4.1.3_external_type.patch
  tar zxf sleuthkit-4.1.3.tar.gz
  patch -u -p0 < tsk4.1.3_external_type.patch
  cd sleuthkit-4.1.3
  # Exclude some pieces of sleuthkit we don't use
  ./configure --disable-java --without-libewf --without-afflib
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

# Use rekall script to install yara as a static library
function install_yara() {
  git clone https://github.com/google/rekall.git
  cd rekall
  git submodule update --init --recursive
  cd third_party/python-yara/
  python setup.py install
  python -c "import yara"
  cd ../../../
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
    brew install git
    install_python_deps
    install_sleuthkit
    install_pytsk
    install_yara
    ;;
esac
