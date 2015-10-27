#!/bin/bash

# Install build dependencies from source.  This script is designed to run on
# Ubuntu systems as old as Ubuntu Lucid (10.04.4) and CentOS 5.11.

set -e

function system_update() {
  if [ $DISTRO == "Ubuntu" ]; then
    apt-get --yes update
    apt-get --yes upgrade
    apt-get --force-yes --yes install git-core
  elif [ $DISTRO == "CentOS" ]; then
    # Required for git
    yum install -y epel-release

    yum -y update
    yum install -y make automake gcc gcc-c++ kernel-devel libtool swig glibc-devel git perl
    echo /usr/local/lib > /etc/ld.so.conf.d/libc.conf
    echo 'PATH=$PATH:/usr/local/bin:/sbin; export PATH' > /etc/profile.d/localbin.sh
    source /etc/profile.d/localbin.sh

    # SElinux gets in the way of python building properly, error is "cannot
    # restore segment prot after reloc: Permission denied".  Disable it.
    /usr/sbin/setenforce 0
    sed -i s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config
  fi
}

# Get a more modern version of openssl than is available on lucid.
function install_openssl() {
  SSL_VERSION=1.0.2d
  SSL_SHA256=671c36487785628a703374c652ad2cebea45fa920ae5681515df25d9f2c9a8c8
  if [ -x "${WGET}" ]; then
    ${WGET} https://www.openssl.org/source/openssl-${SSL_VERSION}.tar.gz
  else
    # wget on CentOS 5.11 can't establish an SSL connection to openssl.org. So
    # we use HTTP and verify hash.
    RETRIEVED_HASH=$(wget -q -O - http://www.openssl.org/source/openssl-${SSL_VERSION}.tar.gz | tee openssl-${SSL_VERSION}.tar.gz | sha256sum | cut -d' ' -f1)
    if [ "${RETRIEVED_HASH}" != "${SSL_SHA256}" ]; then
      echo "Bad hash for openssl-${SSL_VERSION}.tar.gz, quitting"
      exit 1
    fi
  fi
  tar zxf openssl-${SSL_VERSION}.tar.gz
  cd openssl-${SSL_VERSION}
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
function install_wget() {
  WGET_VERSION=1.16
  wget --quiet https://ftp.gnu.org/gnu/wget/wget-${WGET_VERSION}.tar.gz || ${WGET} https://ftp.gnu.org/gnu/wget/wget-${WGET_VERSION}.tar.gz
  tar zxvf wget-${WGET_VERSION}.tar.gz
  cd wget-${WGET_VERSION}
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

  if [ $DISTRO == "Ubuntu" ]; then
    # This is essentially "apt-get install build-dep python2.6" but without
    # libssl-dev so we don't end up using the wrong headers
    apt-get --force-yes --yes install build-essential autoconf automake autotools-dev blt blt-dev cvs debhelper fontconfig-config gdb gettext html2text intltool-debian libbluetooth-dev libbluetooth3 libbz2-dev libcroco3 libdb4.8-dev libexpat1-dev libffi-dev libfile-copy-recursive-perl libfontconfig1 libfontconfig1-dev libfontenc1 libfreetype6-dev libgl1-mesa-dri libgl1-mesa-glx libice6 libjpeg62 liblcms1 libmail-sendmail-perl libncurses5-dev libncursesw5-dev libpaper-utils libpaper1 libpthread-stubs0 libpthread-stubs0-dev libreadline-dev libreadline6-dev libsm6 libsqlite3-dev libsys-hostname-long-perl libxext-dev libxfixes3 libxft-dev libxft2 libxi6 libxinerama1 libxmu6 libxpm4 libxrender-dev libxrender1 libxslt1.1 libxss-dev libxss1 libxt6 libxtst6 libxv1 libxxf86dga1 libxxf86vm1 m4 pkg-config po-debconf python-docutils python-imaging python-jinja2 python-lxml python-pygments python-roman python-sphinx sharutils tcl8.5 tcl8.5-dev tk8.5 tk8.5-dev ttf-dejavu-core update-inetd x11-common x11-utils x11proto-core-dev x11proto-input-dev x11proto-kb-dev x11proto-render-dev x11proto-scrnsaver-dev x11proto-xext-dev xbitmaps xterm xtrans-dev zlib1g-dev libx11-dev libxau-dev libxaw7 libxcb1-dev libxdamage1 libxdmcp-dev zlib1g-dev bzip2 libncurses-dev sqlite3 libgdbm-dev libdb-dev readline-common libpcap-dev
  elif [ $DISTRO == "CentOS" ]; then
    yum install -y zlib-devel bzip2-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel
  fi

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

  # Check we got SSL built, python build considers it non-fatal.
  python2.7 -c "import ssl"
}

# Get a newer protobuf library than what lucid has. Just installing the python
# package isn't enough because we need the compiler and associated libraries.
# This version needs to stay in sync with the requirements.txt python version.
function install_protobuf_libs() {
  ${WGET} https://github.com/google/protobuf/releases/download/v2.6.1/protobuf-2.6.1.tar.gz
  tar zxvf protobuf-2.6.1.tar.gz
  cd protobuf-2.6.1
  ./configure
  make -j4

  # 32bit CentOS fails 'make check' due to it having an older version of gcc
  # with this issue:
  # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=13358
  if [ $DISTRO == "CentOS" ] && [ $(uname -m) != 'x86_64' ]; then
    make install
  else
    make check -j4
    make install
  fi
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

  # lucid packaged version of virtualenv is too old for the next part to work,
  # get a newer version
  pip2.7 install virtualenv

  if [ $DISTRO == "Ubuntu" ]; then
    # Required for M2Crypto matplotlib and numpy
    apt-get --force-yes --yes install swig libpng-dev
  elif [ $DISTRO == "CentOS" ]; then
    # Required for matplotlib and numpy
    yum install -y libpng-devel freetype-devel patch
  fi

  /usr/local/bin/virtualenv -p /usr/local/bin/python2.7 PYTHON_ENV
  source PYTHON_ENV/bin/activate
  pip2.7 install -r /grr/client/linux/requirements.txt

  # protobuf uses a fancy egg format which seems to mess up PyInstaller,
  # resulting in missing the library entirely. I believe the issue is this:
  # https://github.com/pypa/pip/issues/3#issuecomment-1659959
  # Using --egg installs it in a way that PyInstaller understands
  pip2.7 install --egg protobuf==2.6.1

  # That isn't even enough, pyinstaller still fails to include it because there
  # is no __init__.py:
  # https://github.com/google/protobuf/issues/713
  touch PYTHON_ENV/lib/python2.7/site-packages/google/__init__.py

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
  python2.7 -c "import M2Crypto"
}

function install_sleuthkit() {
  ${WGET} -O sleuthkit-4.1.3.tar.gz https://sourceforge.net/projects/sleuthkit/files/sleuthkit/4.1.3/sleuthkit-4.1.3.tar.gz/download
  # Segfault fix: https://github.com/py4n6/pytsk/wiki/Building-SleuthKit
  ${WGET} https://googledrive.com/host/0B3fBvzttpiiScUxsUm54cG02RDA/tsk4.1.3_external_type.patch
  tar zxf sleuthkit-4.1.3.tar.gz
  patch -u -p0 < tsk4.1.3_external_type.patch
  cd sleuthkit-4.1.3
  # Exclude some pieces of sleuthkit we don't use
  ./configure --disable-java --without-libewf --without-afflib
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
function install_packagetools() {
  if [ $DISTRO == "Ubuntu" ]; then
    apt-get --force-yes --yes install po4a
    ${WGET} http://ftp.debian.org/debian/pool/main/d/debhelper/debhelper_9.20150101.tar.gz
    tar zxf debhelper_9.20150101.tar.gz
    cd debhelper
    make -j4
    make install
    cd -
  elif [ $DISTRO == "CentOS" ]; then
    yum install -y rpm-build
  fi
}

function usage() {
  echo "Usage: install_linux.sh [DISTRO_NAME]"
  exit
}

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

if [ $# -ne 1 ]; then
  usage
fi

DISTRO=$1
if [ $DISTRO == "Ubuntu" ]; then
  WGET="/usr/local/bin/wget --ca-directory=/etc/ssl/certs --quiet"
elif [ $DISTRO == "CentOS" ]; then
  WGET="/usr/local/bin/wget --ca-certificate=/etc/pki/tls/certs/ca-bundle.crt --quiet"
else
  usage
fi

system_update
install_openssl
install_wget
install_python_from_source
install_protobuf_libs
install_python_deps
install_m2crypto
install_sleuthkit
install_pytsk
# TODO: find a way to install yara on linux that actually works on lucid with
# recent openssl.
#install_yara
install_packagetools
echo "Build environment provisioning complete."
