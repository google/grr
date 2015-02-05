#!/bin/bash

# Install build dependencies from source.  This script is designed to run on
# ubuntu systems as old as ubuntu lucid (10.04.4). We choose lucid so that GRR
# will run on ubuntu linux machines at least as old as this.

set -e

# Update the system
function apt_get_update() {
  apt-get --yes update
  apt-get --yes upgrade
}

# Get a more modern version of openssl than is available on lucid
function install_openssl() {
  wget --quiet https://www.openssl.org/source/openssl-1.0.2.tar.gz
  tar zxf openssl-1.0.2.tar.gz
  cd openssl-1.0.2
  ./config -fPIC
  # openssl doesn't play nice with jobserver so no -j4
  make
  make install
  cd -
  echo /usr/local/ssl/lib > /etc/ld.so.conf.d/ssl.conf
  ln -s /usr/local/ssl/include/openssl/ /usr/include/openssl
  ldconfig
  export LDFLAGS='-L/usr/local/ssl/lib'
  export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/ssl/lib
}

# The wget shipped with lucid doesn't support SANs in SSL certs which breaks
# lots of the downloads https://savannah.gnu.org/bugs/index.php?20421
WGET="/usr/local/bin/wget --ca-directory=/etc/ssl/certs --quiet"
function install_wget() {
  wget --quiet https://ftp.gnu.org/gnu/wget/wget-1.16.tar.gz
  tar zxvf wget-1.16.tar.gz
  cd wget-1.16
  ./configure --with-ssl=openssl
  make -j4
  make install
  ldconfig
  cd -
  # New OpenSSL uses a different hashing scheme, if we don't do this wget will
  # fail to find the right certificate, but we have to wait until after we use
  # the existing wget above.
  # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=611102
  /usr/local/ssl/bin/c_rehash /etc/ssl/certs/
}

# We need a newer version of python that what lucid ships with.
function install_python_from_source() {
  # This is essentially "apt-get install build-dep python2.6" but without
  # libssl-dev so we don't end up using the wrong headers
  apt-get --force-yes --yes install build-essential autoconf automake autotools-dev blt blt-dev cvs debhelper fontconfig-config gdb gettext html2text intltool-debian libbluetooth-dev libbluetooth3 libbz2-dev libcroco3 libdb4.8-dev libexpat1-dev libffi-dev libfile-copy-recursive-perl libfontconfig1 libfontconfig1-dev libfontenc1 libfreetype6-dev libgl1-mesa-dri libgl1-mesa-glx libice6 libjpeg62 liblcms1 libmail-sendmail-perl libncurses5-dev libncursesw5-dev libpaper-utils libpaper1 libpthread-stubs0 libpthread-stubs0-dev libreadline-dev libreadline6-dev libsm6 libsqlite3-dev libsys-hostname-long-perl libxext-dev libxfixes3 libxft-dev libxft2 libxi6 libxinerama1 libxmu6 libxpm4 libxrender-dev libxrender1 libxslt1.1 libxss-dev libxss1 libxt6 libxtst6 libxv1 libxxf86dga1 libxxf86vm1 m4 pkg-config po-debconf python-docutils python-imaging python-jinja2 python-lxml python-pygments python-roman python-sphinx sharutils tcl8.5 tcl8.5-dev tk8.5 tk8.5-dev ttf-dejavu-core update-inetd x11-common x11-utils x11proto-core-dev x11proto-input-dev x11proto-kb-dev x11proto-render-dev x11proto-scrnsaver-dev x11proto-xext-dev xbitmaps xterm xtrans-dev zlib1g-dev libx11-dev libxau-dev libxaw7 libxcb1-dev libxdamage1 libxdmcp-dev zlib1g-dev bzip2 libncurses-dev sqlite3 libgdbm-dev libdb-dev readline-common libpcap-dev

  ${WGET} https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz
  tar zxvf Python-2.7.9.tgz
  cd Python-2.7.9

  # --enabled-shared for better performance, discussed in some detail here:
  # https://code.google.com/p/modwsgi/wiki/InstallationIssues
  ./configure --enable-shared --enable-ipv6

  # We ignore these unfulfilled dependencies:
  # bsddb185, dl, imageop, sunaudiodev
  # http://stackoverflow.com/questions/3813092/ubuntu-packages-needed-to-compile-python-2-7
  make -j4
  make install
  ldconfig
  cd -
}

# Get a newer protobuf library than what lucid has. Just installing the python
# package isn't enough because we need the compiler and associated libraries.
# This version needs to stay in sync with the requirements.txt python version.
function install_protobuf_libs() {
  ${WGET} https://protobuf.googlecode.com/svn/rc/protobuf-2.6.0.tar.gz
  tar zxvf protobuf-2.6.0.tar.gz
  cd protobuf-2.6.0
  ./configure
  make -j4
  make check -j4
  make install
  ldconfig
  cd -
}

# Install our python dependencies into a virtualenv that uses the new python
# version
function install_python_deps() {
  # Bootstrap to a newer pip. We do it this way so that packages get installed
  # into our new python2.7 directory.
  ${WGET} https://bootstrap.pypa.io/get-pip.py
  python2.7 get-pip.py
  pip2.7 install --upgrade pip

  # lucid packaged version of virtualenv is too old for the next line to work,
  # get a newer version
  pip2.7 install virtualenv

  # Required for M2Crypto
  apt-get --force-yes --yes install swig

  /usr/local/bin/virtualenv -p /usr/local/bin/python2.7 PYTHON_ENV
  source PYTHON_ENV/bin/activate
  pip2.7 install -r /grr/requirements.txt
}

# Install patched m2crypto, hopefully this patch will eventually be accepted so
# we don't have to do this and can just add a line to requirements.txt
# https://github.com/M2Crypto/M2Crypto/pull/16
function install_m2crypto() {
  ${WGET} https://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-0.22.3.tar.gz#md5=573f21aaac7d5c9549798e72ffcefedd
  ${WGET} https://googledrive.com/host/0B1wsLqFoT7i2aW5mWXNDX1NtTnc/m2crypto-0.22.3-fixes.patch
  tar zxf M2Crypto-0.22.3.tar.gz
  cd M2Crypto-0.22.3
  patch -u -p1 < ../m2crypto-0.22.3-fixes.patch
  python2.7 setup.py build
  python2.7 setup.py install
  cd -
}

function install_sleuthkit() {
  ${WGET} -O sleuthkit-3.2.3.tar.gz https://sourceforge.net/projects/sleuthkit/files/sleuthkit/3.2.3/sleuthkit-3.2.3.tar.gz/download
  tar zxf sleuthkit-3.2.3.tar.gz
  cd sleuthkit-3.2.3
  ./configure
  make -j4
  make install
  ldconfig
  cd -
}

function install_pytsk() {
  ${WGET} https://github.com/py4n6/pytsk/releases/download/20150111/pytsk-20150111.tgz
  tar zxf pytsk-20150111.tgz
  cd pytsk
  python2.7 setup.py build
  python2.7 setup.py install
  cd -
}

# Lucid debhelper is too old to build debs that handle both upstart and init.d
function install_debhelper() {
  apt-get --force-yes --yes install po4a
  ${WGET} http://ftp.debian.org/debian/pool/main/d/debhelper/debhelper_9.20150101.tar.gz
  tar zxf debhelper_9.20150101.tar.gz
  cd debhelper
  make -j4
  make install
  cd -
}

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

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
