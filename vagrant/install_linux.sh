#!/bin/bash

# This script installs all dependencies and is run as part of vagrant
# provisioning. It is designed to run on
# Ubuntu systems as old as Ubuntu Lucid (10.04.4) and CentOS 5.11.

set -e
set -x

INSTALL_USER="vagrant"

function system_update() {
  if [ $DISTRO == "Ubuntu" ]; then
    # Fix for old Vagrant versions to boot precise64, see
    # https://github.com/mitchellh/vagrant/issues/289
    if [ "${CODENAME}" == "precise" ]; then
      echo "set grub-pc/install_devices /dev/sda" | debconf-communicate
    fi
    # Lucid is EOL as of April 2015. We can continue to support it with GRR like
    # this, but there's definitely no security updates so we will want to drop
    # it at some point.
    if [ "${CODENAME}" == "lucid" ]; then
      echo Fixing sources.list to point at old-releases.ubuntu.com
      sudo sed -i s'/us\.archive\.ubuntu\.com/old\-releases\.ubuntu\.com/' /etc/apt/sources.list
      sudo sed -i s'/security\.ubuntu\.com/old\-releases\.ubuntu\.com/' /etc/apt/sources.list
    fi
    apt-get --yes update
    apt-get --yes upgrade
    apt-get --force-yes --yes install git-core unzip swig build-essential
  elif [ $DISTRO == "CentOS" ]; then
    # Required for git
    yum install -y epel-release

    yum -y update
    yum install -y make automake gcc gcc-c++ kernel-devel libtool swig glibc-devel git perl libffi-devel
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
  SSL_VERSION=1.0.2j
  SSL_SHA256=e7aff292be21c259c6af26469c7a9b3ba26e9abaaffd325e3dccc9785256c431
  if [ -x "${WGET}" ]; then
    ${WGET} https://www.openssl.org/source/openssl-${SSL_VERSION}.tar.gz
  else
    # wget on CentOS 5.11 and Ubuntu lucid can't establish an SSL connection to
    # openssl.org because everything before TLSv1.1 is explicitly dropped. So
    # we use a HTTP mirror and verify hash.
    RETRIEVED_HASH=$(wget -q -O - http://artfiles.org/openssl.org/source/openssl-${SSL_VERSION}.tar.gz | tee openssl-${SSL_VERSION}.tar.gz | sha256sum | cut -d' ' -f1)
    if [ "${RETRIEVED_HASH}" != "${SSL_SHA256}" ]; then
      echo "Bad hash for openssl-${SSL_VERSION}.tar.gz, quitting"
      exit 1
    fi
  fi
  tar zxf openssl-${SSL_VERSION}.tar.gz
  cd openssl-${SSL_VERSION}
  # We want cryptography to dynamically link openssl, so we need to build the
  # shared library. Pyinstaller will ship the lib for us. If we statically link,
  # selinux policy on centos will break installation.
  ./config shared -fPIC
  # openssl doesn't play nice with jobserver so no -j4
  make
  make install
  cd -
  echo /usr/local/ssl/lib > /etc/ld.so.conf.d/ssl.conf
  if [ ! -e /usr/include/openssl ]; then
    ln -s /usr/local/ssl/include/openssl/ /usr/include/openssl
  fi;
  ldconfig
  export LDFLAGS='-L/usr/local/ssl/lib'
  export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/ssl/lib
}

# The wget shipped with lucid doesn't support SANs in SSL certs which breaks
# lots of the downloads https://savannah.gnu.org/bugs/index.php?20421
function install_wget() {
  WGET_VERSION=1.16
  wget --quiet --ca-directory=/etc/ssl/certs https://ftp.gnu.org/gnu/wget/wget-${WGET_VERSION}.tar.gz || ${WGET} https://ftp.gnu.org/gnu/wget/wget-${WGET_VERSION}.tar.gz
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
  PYTHON_VERSION=2.7.13

  if [ $DISTRO == "Ubuntu" ]; then
    # This is essentially "apt-get build-dep python2.6|7" but without
    # libssl-dev so we don't end up using the wrong headers
    if [ "${CODENAME}" == "lucid" ]; then
      apt-get --force-yes --yes install build-essential autoconf automake autotools-dev blt blt-dev cvs debhelper fontconfig-config gdb gettext html2text intltool-debian libbluetooth-dev libbluetooth3 libbz2-dev libcroco3 libdb4.8-dev libexpat1-dev libffi-dev libfile-copy-recursive-perl libfontconfig1 libfontconfig1-dev libfontenc1 libfreetype6-dev libgl1-mesa-dri libgl1-mesa-glx libice6 libjpeg62 liblcms1 libmail-sendmail-perl libncurses5-dev libncursesw5-dev libpaper-utils libpaper1 libpthread-stubs0 libpthread-stubs0-dev libreadline-dev libreadline6-dev libsm6 libsqlite3-dev libsys-hostname-long-perl libxext-dev libxfixes3 libxft-dev libxft2 libxi6 libxinerama1 libxmu6 libxpm4 libxrender-dev libxrender1 libxslt1.1 libxss-dev libxss1 libxt6 libxtst6 libxv1 libxxf86dga1 libxxf86vm1 m4 pkg-config po-debconf python-docutils python-imaging python-jinja2 python-lxml python-pygments python-roman python-sphinx sharutils tcl8.5 tcl8.5-dev tk8.5 tk8.5-dev ttf-dejavu-core update-inetd x11-common x11-utils x11proto-core-dev x11proto-input-dev x11proto-kb-dev x11proto-render-dev x11proto-scrnsaver-dev x11proto-xext-dev xbitmaps xterm xtrans-dev zlib1g-dev libx11-dev libxau-dev libxaw7 libxcb1-dev libxdamage1 libxdmcp-dev zlib1g-dev bzip2 libncurses-dev sqlite3 libgdbm-dev libdb-dev readline-common libpcap-dev
    elif [ "${CODENAME}" == "precise" ]; then
      apt-get --force-yes --yes install build-essential autoconf automake autotools-dev blt blt-dev debhelper dh-apparmor diffstat docutils-common gdb gettext help2man html2text intltool-debian libbluetooth-dev libbluetooth3 libbz2-dev libcroco3 libdb5.1-dev libexpat1-dev libffi-dev libfontconfig1-dev libfreetype6-dev libgdbm-dev libgettextpo0 libjs-sphinxdoc libjs-underscore libncursesw5-dev libpthread-stubs0 libpthread-stubs0-dev libreadline-dev libreadline6-dev libsqlite3-dev libtinfo-dev libunistring0 libx11-dev libxau-dev libxcb1-dev libxdmcp-dev libxext-dev libxft-dev libxrender-dev libxss-dev libxss1 m4 pkg-config po-debconf python-docutils python-jinja2 python-markupsafe python-pygments python-roman python-sphinx quilt sharutils sphinx-common tcl8.5 tcl8.5-dev tk8.5 tk8.5-dev x11proto-core-dev x11proto-input-dev x11proto-kb-dev x11proto-render-dev x11proto-scrnsaver-dev x11proto-xext-dev xorg-sgml-doctools xtrans-dev xvfb zlib1g-dev
    else
      echo "Only supporting precise and lucid"
      exit 1
    fi
  elif [ $DISTRO == "CentOS" ]; then
    yum install -y zlib-devel bzip2-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel
  fi

  ${WGET} https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
  tar zxvf Python-${PYTHON_VERSION}.tgz
  cd Python-${PYTHON_VERSION}

  # --enabled-shared for better performance, discussed in some detail here:
  # https://code.google.com/p/modwsgi/wiki/InstallationIssues
  ./configure --enable-shared --enable-ipv6 --enable-unicode=ucs4

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
}

# Lucid debhelper is too old to build debs that handle both upstart, init.d,
# systemd
function install_packagetools() {
  if [ $DISTRO == "Ubuntu" ]; then
    DH_SHA256=fd8d81d71d1bb0ba4b58c517465551231dd60811b98c867e4344bc55ec6a45f2
    apt-get --force-yes --yes install po4a
    ${WGET} http://ftp.debian.org/debian/pool/main/d/debhelper/debhelper_9.20150101.tar.gz
    RETRIEVED_HASH=$(${WGET} -q -O - http://ftp.debian.org/debian/pool/main/d/debhelper/debhelper_9.20150101.tar.gz | tee debhelper_9.20150101.tar.gz | sha256sum | cut -d' ' -f1)
    if [ "${RETRIEVED_HASH}" != "${DH_SHA256}" ]; then
      echo "Bad hash for debhelper_9.20150101.tar.gz, quitting"
      exit 1
    fi

    tar zxf debhelper_9.20150101.tar.gz
    cd debhelper
    make -j4
    make install
    cd -
  elif [ $DISTRO == "CentOS" ]; then
    yum install -y rpm-build
  fi
}

function install_proto_compiler {
  VERSION=3.2.0
  ARCH=$(uname -m)
  # Get arch in the format that the protobuf urls use
  if [ "${ARCH}" == "i686" ]; then
    ARCH="x86_32"
  fi

  PROTO_DIR=/home/${INSTALL_USER}/protobuf

  if [ ! -d "${PROTO_DIR}/bin" ]; then
    cwd=$(pwd)
    mkdir -p "${PROTO_DIR}"
    cd "${PROTO_DIR}"
    ${WGET} "https://github.com/google/protobuf/releases/download/v${VERSION}/protoc-${VERSION}-linux-${ARCH}.zip"
    unzip "protoc-${VERSION}-linux-${ARCH}.zip"
    chmod -R a+rx "${PROTO_DIR}"
    echo export PROTOC="${PROTO_DIR}/bin/protoc" >> /etc/profile
    cd "${cwd}"
  else
    echo "protoc already installed in ${PROTO_DIR}"
  fi
}

function usage() {
  echo "Usage: install_linux.sh [Ubuntu|CentOS]"
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
CODENAME=$(lsb_release -cs)

system_update
install_openssl
install_wget
install_python_from_source
install_python_deps
install_packagetools
install_proto_compiler
echo "Build environment provisioning complete."
