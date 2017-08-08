#!/bin/bash
#
# Script to install GRR from scratch on an Ubuntu system. Ubuntu xenial is the
# only supported platform.
#
set -e

# If true, do an apt-get upgrade
: ${UPGRADE:=true}

DEB_PACKAGE="grr-server_3.1.0-2_amd64.deb"
DEB_URL="https://storage.googleapis.com/releases.grr-response.com/3.1.0.2/${DEB_PACKAGE}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root"
  exit 1
fi

echo "Installation only supported on Ubuntu Xenial"
# This will return non-zero on non-xenial systems and cause an exit
grep xenial /etc/lsb-release

echo "Updating APT."
apt-get --yes update

if $UPGRADE; then
  echo "Upgrading existing packages."
  apt-get --yes upgrade
fi

echo "Installing dependencies."
# The packaging tools here are used to repack the linux client installers.
apt-get install -y \
  debhelper \
  dpkg-dev \
  python-dev \
  python-pip \
  rpm \
  wget \
  zip

wget "${DEB_URL}"
dpkg -i "${DEB_PACKAGE}"

HOSTNAME=$(hostname)
echo "Install complete. Congratulations. Point your browser at http://${HOSTNAME}:8000"
