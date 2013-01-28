#!/bin/bash
#
# Script to install GRR from scratch on an Ubuntu 12.04 or 12.10 system.
#
# By default this will install into /usr and set the config in
# /etc/grr/grr-server.conf
#

if [ -z "${GRR_TEST_VERSIONS}" ];
then
  GRR_TEST_VERSIONS=0;
else
  GRR_TEST_VERSIONS=1;
  echo "Running with Beta test versions"
fi

PREFIX=/usr

# URL to read the latest version URLs from
if [ $GRR_TEST_VERSIONS = 0 ]; then
  VERSION_URL=https://grr.googlecode.com/files/latest_versions.txt
else
  VERSION_URL=https://grr.googlecode.com/files/latest_versions_test.txt
fi

# Variables to control the install versions etc. Made for changing this to
# support other platforms more easily.
PLAT=amd64
INSTALL_DIR=${PREFIX}/share/grr
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
  if [ ${ALL_YES} = 0 ]; then
    echo ""
    read -p "Run ${CMD} [Y/n/a]? " REPLY
    case $REPLY in
      y|Y|'') run_header ${CMD};;
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
run_cmd_confirm sudo apt-get --yes update;
run_cmd_confirm sudo apt-get --yes upgrade;
run_cmd_confirm sudo apt-get --yes install python-setuptools python-dateutil python-django ipython apache2-utils zip wget python-ipaddr python-support python-psutil python-matplotlib;


header "Getting the right version of M2Crypto installed"
run_cmd_confirm sudo apt-get --yes remove python-m2crypto;
run_cmd_confirm wget --no-verbose https://grr.googlecode.com/files/${DEB_DEPENDENCIES} -O ${DEB_DEPENDENCIES};
run_cmd_confirm tar zxfv ${DEB_DEPENDENCIES};
run_cmd_confirm sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${M2CRYPTO_DEB};

header "Installing Protobuf"
run_cmd_confirm sudo apt-get --yes install libprotobuf-dev python-protobuf;

header "Installing Sleuthkit and Pytsk"
run_cmd_confirm sudo apt-get --yes remove libtsk3* sleuthkit
run_cmd_confirm sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${SLEUTHKIT_DEB} ${DEB_DEPENDENCIES_DIR}/${PYTSK_DEB};

header "Installing Mongodb"
run_cmd_confirm sudo apt-get --yes install mongodb python-pymongo;

header "Getting correct psutil version (we require 0.6 or newer)"
PSUTIL_VERSION=`dpkg-query -W python-psutil | cut -f 2`
if [[ "$PSUTIL_VERSION" == 0.5* ]]; then
  echo "Unsupported psutil version ${PSUTIL_VERSION}. Upgrading with pip."
  run_cmd_confirm sudo apt-get --yes remove python-psutil;
  run_cmd_confirm sudo apt-get --yes install python-pip build-essential python-dev;
  run_cmd_confirm sudo easy_install psutil;
fi

header "Checking Django version is > 1.4 and fixing up"
# We need 1.4, 12.04 ships with 1.3
DJANGO_VERSION=`dpkg-query -W python-django | cut -f 2`
if [[ "$DJANGO_VERSION" == 1.3* ]]; then
  echo "Unsupported Django version ${DJANGO_VERSION}. Upgrading with pip."
  run_cmd_confirm sudo apt-get --yes remove python-django
  run_cmd_confirm sudo easy_install django
fi

header "Getting latest package information from repo"
VERSION_FILE=$(basename ${VERSION_URL});
run_cmd_confirm wget --no-verbose ${VERSION_URL} -O ${VERSION_FILE};
SERVER_DEB_URL=$(grep grr-server ${VERSION_FILE} | grep $PLAT | cut -f 2);
SERVER_DEB=$(basename ${SERVER_DEB_URL});
run_cmd_confirm rm -f ${VERSION_FILE}

header "Installing GRR from prebuilt package"
run_cmd_confirm wget --no-verbose ${SERVER_DEB_URL} -O ${SERVER_DEB};
run_cmd_confirm sudo dpkg -i ${SERVER_DEB};

header "Initialize the configuration, building clients and setting options."
run_cmd_confirm grr_config_updater.py initialize

header "Enable grr-single-server to start automatically on boot"
SERVER_DEFAULT=/etc/default/grr-single-server
run_cmd_confirm sudo sed -i 's/START=\"no\"/START=\"yes\"/' ${SERVER_DEFAULT};

header "Starting up the service"
sudo initctl status grr-single-server | grep "running"
IS_RUNNING=$?
if [ $IS_RUNNING = 0 ]; then
  run_cmd_confirm sudo initctl stop grr-single-server
fi
run_cmd_confirm sudo initctl start grr-single-server

HOSTNAME=`hostname`
echo "############################################################################################"
echo "Install complete. Congratulations. Point your browser at http://${HOSTNAME}:8000"
echo "############################################################################################"
echo ""
