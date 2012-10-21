#!/bin/bash
#
# Script to install GRR from scratch on an Ubuntu 12.04 system.
#
# By default this will generate keys in /etc/grr/keys and install into /usr
#

# URL to read the latest version URLs from
VERSION_URL=https://grr.googlecode.com/files/latest_versions.txt

# Variables to control the install versions etc. Made for changing this to
# support other platforms more easily.
PLAT=amd64
INSTALL_DIR=/usr/share/grr
DEB_DEPENDENCIES=ubuntu-12.04-${PLAT}-debs.tar.gz;
DEB_DEPENDENCIES_DIR=ubuntu-12.04-${PLAT}-debs;
SLEUTHKIT_DEB=sleuthkit-lib_3.2.3-1_${PLAT}.deb
PYTSK_DEB=pytsk3_3.2.3-1_${PLAT}.deb
M2CRYPTO_DEB=m2crypto_0.21.1-1_${PLAT}.deb

# Variable to store if the user has answered "Yes to All"
ALL_YES=0;


function header()
{
  echo ""
  echo "##########################################################################################"
  echo "     ${*}";
  echo "##########################################################################################"
}

function run_header()
{
  echo "#### Running #### ${*}"
}


function exit_fail()
{
  FAIL=$*;
  echo "#########################################################################################";
  echo "FAILURE RUNNING: ${FAIL}";
  echo "#########################################################################################";
  exit 0
}


function run_cmd_confirm()
{
  CMD=$*;
  echo ""
  if [ ${ALL_YES} = 0 ]; then
    read -p "Run ${CMD} [y/N/a]? " REPLY
    case $REPLY in
      y|Y) run_header ${CMD};;
      a|A) echo "Answering yes from now on"; ALL_YES=1;;
      *) return ;;
    esac
  fi
  ${CMD};
  RETVAL=$?
  if [ $RETVAL -ne 0 ]; then
    exit_fail $CMD;
  fi
};


header "Updating APT and Installing dependencies"
run_cmd_confirm sudo apt-get update;
run_cmd_confirm sudo apt-get upgrade;
run_cmd_confirm sudo apt-get --yes install python-setuptools python-dateutil python-django ipython apache2-utils zip wget python-ipaddr;


header "Getting the right version of M2Crypto installed"
run_cmd_confirm sudo apt-get --yes remove python-m2crypto;
run_cmd_confirm wget https://grr.googlecode.com/files/${DEB_DEPENDENCIES};
run_cmd_confirm tar zxfv ${DEB_DEPENDENCIES};
run_cmd_confirm sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${M2CRYPTO_DEB};

header "Installing Protobuf"
run_cmd_confirm sudo apt-get --yes install libprotobuf-dev python-protobuf

header "Installing Sleuthkit and Pytsk"
run_cmd_confirm sudo apt-get --yes remove libtsk3* sleuthkit
run_cmd_confirm sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${SLEUTHKIT_DEB} ${DEB_DEPENDENCIES_DIR}/${PYTSK_DEB};

header "Installing Mongodb"
run_cmd_confirm sudo apt-get --yes install mongodb python-pymongo

header "Getting correct psutil version (we require 0.5 or newer)"
run_cmd_confirm sudo apt-get --yes remove python-psutil
run_cmd_confirm sudo apt-get --yes install python-pip build-essential python-dev
run_cmd_confirm sudo easy_install -v psutil


header "Getting latest package information from repo"
run_cmd_confirm wget ${VERSION_URL};
VERSION_FILE=$(basename ${VERSION_URL});
SERVER_DEB_URL=$(grep grr-server ${VERSION_FILE} | grep $PLAT | cut -f 2);
SERVER_DEB=$(basename ${SERVER_DEB_URL});
run_cmd_confirm rm -f ${VERSION_FILE}

header "Installing GRR from prebuilt package"
run_cmd_confirm wget ${SERVER_DEB_URL};
run_cmd_confirm sudo dpkg -i ${SERVER_DEB};

header "Setup Admin UI password/user"
read -p "Which username do you want to use for basic authentication to the Admin UI? e.g. admin. " ADMIN_USER
run_cmd_confirm sudo htpasswd -d -c /etc/grr/grr-ui.htaccess ${ADMIN_USER}

header "Configuring user ${ADMIN_USER} as admin in GRR"
run_cmd_confirm echo "MakeUserAdmin('${ADMIN_USER}')" | /usr/bin/grr-console.py

header "Enable grr-single-server to start automatically on boot"
SERVER_DEFAULT=/etc/default/grr-single-server
run_cmd_confirm sudo sed -i 's/START=\"no\"/START=\"yes\"/' ${SERVER_DEFAULT};
run_cmd_confirm sudo initctl start grr-single-server

header "Updating clients from the repo"
run_cmd_confirm sudo ${INSTALL_DIR}/scripts/update_clients.sh

header "Building clients"
run_cmd_confirm sudo ${INSTALL_DIR}/scripts/build_clients.sh

header "Installing memory drivers"
run_cmd_confirm sudo ${INSTALL_DIR}/scripts/install_memory_drivers.sh

HOSTNAME=`hostname`
echo "############################################################################################"
echo "Install complete. Congratulations. Point your browser at http://${HOSTNAME}:8000"
echo "############################################################################################"
echo ""
