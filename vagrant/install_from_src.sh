#!/bin/bash

# Install build dependencies from source.  This script is designed to run on
# ubuntu systems as old as ubuntu lucid (10.04.4). We choose lucid so that GRR
# will run on ubuntu linux machines at least as old as this.

# Update the system
function apt_get_update() {
  sudo apt-get --yes update
  sudo apt-get --yes upgrade
}

# Get a more modern version of openssl than is available on lucid
function install_openssl() {
  wget --quiet https://www.openssl.org/source/openssl-1.0.1l.tar.gz
  tar zxf openssl-1.0.1l.tar.gz
  cd openssl-1.0.1l
  ./config
  make -j4
  make test
  sudo make install
  sudo ldconfig
  cd -
}

# The wget shipped with lucid doesn't support SANs in SSL certs which breaks
# lots of the downloads https://savannah.gnu.org/bugs/index.php?20421
WGET=/usr/local/bin/wget
function install_wget() {
  wget --quiet https://ftp.gnu.org/gnu/wget/wget-1.16.tar.gz
  tar zxvf wget-1.16.tar.gz
  cd wget-1.16
  ./configure --with-ssl=openssl
  make -j4
  sudo make install
  sudo ldconfig
  cd -
}

# We need a newer version of python that what lucid ships with.
function install_python_from_source() {
  sudo apt-get --force-yes --yes build-dep python2.6
  sudo apt-get --force-yes --yes install zlib1g-dev bzip2 libncurses-dev sqlite3 libgdbm-dev libdb-dev readline-common tk-dev libpcap-dev

  ${WGET} --quiet https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz
  tar zxvf Python-2.7.9.tgz
  cd Python-2.7.9

  # --enabled-shared for better performance, discussed in some detail here:
  # https://code.google.com/p/modwsgi/wiki/InstallationIssues
  ./configure --enable-shared --enable-ipv6

  # We ignore these unfulfilled dependencies:
  # bsddb185, dl, imageop, sunaudiodev
  # http://stackoverflow.com/questions/3813092/ubuntu-packages-needed-to-compile-python-2-7
  make -j4
  sudo make install
  sudo ldconfig
  cd -
}

# Get a newer protobuf library than what lucid has. Just installing the python
# package isn't enough because we need the compiler and associated libraries.
# This version needs to stay in sync with the requirements.txt python version.
function install_protobuf_libs() {
  ${WGET} --quiet https://protobuf.googlecode.com/svn/rc/protobuf-2.6.0.tar.gz
  tar zxvf protobuf-2.6.0.tar.gz
  cd protobuf-2.6.0
  ./configure
  make -j4
  make check -j4
  sudo make install
  sudo ldconfig
  cd -
}

# Install our python dependencies into a virtualenv that uses the new python
# version
function install_python_deps() {
  sudo apt-get --force-yes --yes install python-setuptools

  # Get a better version of pip itself
  sudo easy_install pip

  # lucid packaged version of virtualenv is too old for the next line to work,
  # get a newer version
  sudo pip install virtualenv

  # Required for M2Crypto
  sudo apt-get --force-yes --yes install swig

  /usr/local/bin/virtualenv -p /usr/local/bin/python2.7 PYTHON_ENV
  source PYTHON_ENV/bin/activate
  pip install -r /grr/requirements.txt
}

# Install patched m2crypto, hopefully this patch will eventually be accepted so
# we don't have to do this and can just add a line to requirements.txt
# https://github.com/M2Crypto/M2Crypto/pull/16
function install_m2crypto() {
  ${WGET} --quiet https://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-0.22.3.tar.gz#md5=573f21aaac7d5c9549798e72ffcefedd
  ${WGET} --quiet https://googledrive.com/host/0B1wsLqFoT7i2aW5mWXNDX1NtTnc/m2crypto-0.22.3-fixes.patch
  tar zxf M2Crypto-0.22.3.tar.gz
  cd M2Crypto-0.22.3
  patch -u -p1 < ../m2crypto-0.22.3-fixes.patch
  python setup.py build
  python setup.py install
  cd -
}

function install_sleuthkit() {
  ${WGET} -O sleuthkit-3.2.3.tar.gz --quiet https://sourceforge.net/projects/sleuthkit/files/sleuthkit/3.2.3/sleuthkit-3.2.3.tar.gz/download
  tar zxf sleuthkit-3.2.3.tar.gz
  cd sleuthkit-3.2.3
  ./configure
  make -j4
  sudo make install
  sudo ldconfig
  cd -
}

function install_pytsk() {
  ${WGET} --quiet https://github.com/py4n6/pytsk/releases/download/20150111/pytsk-20150111.tgz
  tar zxf pytsk-20150111.tgz
  cd pytsk
  python setup.py build
  python setup.py install
  cd -
}

# Lucid debhelper is too old to build debs that handle both upstart and init.d
function install_debhelper() {
  sudo apt-get --force-yes --yes install po4a
  ${WGET} --quiet http://ftp.debian.org/debian/pool/main/d/debhelper/debhelper_9.20150101.tar.gz
  tar zxf debhelper_9.20150101.tar.gz
  cd debhelper
  make -j4
  sudo make install
  cd -
}

apt_get_update
install_openssl
install_wget
install_python_from_source
install_protobuf_libs
install_python_deps
install_m2crypto
install_sleuthkit
install_pytsk
install_debhelper
