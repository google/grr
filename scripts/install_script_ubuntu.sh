#!/bin/bash
#
# Script to install GRR from scratch on an Ubuntu 12.04, 12.10 or 13.04 system.
#
# By default this will install into /usr and set the config in
# /etc/grr/
#
PREFIX=/usr

# Variables to control the install versions etc. Made for changing this to
# support other platforms more easily.
PLAT=amd64
INSTALL_DIR=${PREFIX}/share/grr

# We now host files on google drive since code.google.com downloads are
# deprecated: https://code.google.com/p/support/wiki/DownloadsFAQ
DEB_DEPENDENCIES_URL=https://googledrive.com/host/0B1wsLqFoT7i2aW5mWXNDX1NtTnc/ubuntu-12.04-${PLAT}-debs.tar.gz;
DEB_DEPENDENCIES_DIR=ubuntu-12.04-${PLAT}-debs;
SLEUTHKIT_DEB=sleuthkit-lib_3.2.3-1_${PLAT}.deb
PYTSK_DEB=pytsk3_3.2.3-1_${PLAT}.deb
M2CRYPTO_DEB=m2crypto_0.21.1-1_${PLAT}.deb

GRR_STABLE_VERSION=0.3.0-2
GRR_TEST_VERSION=0.3.1-1
SERVER_DEB_STABLE_BASE_URL=https://googledrive.com/host/0B1wsLqFoT7i2c3F0ZmI1RDJlUEU/grr-server_
SERVER_DEB_TEST_BASE_URL=https://googledrive.com/host/0B1wsLqFoT7i2c3F0ZmI1RDJlUEU/test-grr-server_


# Take command line parameters as these are easier for users than shell
# variables.
if [ "$1" == "--localtest" ]
then
  GRR_LOCAL_TEST=1;
  GRR_TESTING=1;
elif [ "$1" == "--test" ]
then
  GRR_LOCAL_TEST=0;
  GRR_TESTING=1;
fi


if [ -z "${GRR_TESTING}" ];
then
  SERVER_DEB_URL=${SERVER_DEB_STABLE_BASE_URL}${GRR_STABLE_VERSION}_${PLAT}.deb
else
  echo "#########################################"
  echo "#### Running with Beta test versions ####"
  echo "#########################################"
  SERVER_DEB_URL=${SERVER_DEB_TEST_BASE_URL}${GRR_TEST_VERSION}_${PLAT}.deb
fi

# Used for local testing, if set it will assume the deb is in the current path
# instead of attempting wget for it.
if [ -z "${GRR_LOCAL_TEST}" ];
then
  GRR_LOCAL_TEST=0;
fi


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
run_cmd_confirm sudo apt-get --force-yes --yes install python-setuptools python-dateutil python-django ipython apache2-utils zip wget python-ipaddr python-support python-matplotlib python-mox python-yaml python-pip dpkg-dev debhelper rpm prelink build-essential python-dev python-pandas python-mock;

# Fail silently if python-dev or libpython-dev is not available in the apt repo
# python-dev is for Ubuntu version < 12.10 and libpython-dev is for > 12.04
sudo apt-get --force-yes --yes install python-dev 2>/dev/null
sudo apt-get --force-yes --yes install libpython-dev 2>/dev/null

header "Getting the right version of M2Crypto installed"
run_cmd_confirm sudo apt-get --yes remove python-m2crypto;

DEB_DEPENDENCIES_TARBALL=$(basename ${DEB_DEPENDENCIES_URL});
run_cmd_confirm wget --no-verbose ${DEB_DEPENDENCIES_URL} -O ${DEB_DEPENDENCIES_TARBALL};
run_cmd_confirm tar zxfv ${DEB_DEPENDENCIES_TARBALL};
run_cmd_confirm sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${M2CRYPTO_DEB};

header "Installing Protobuf"
run_cmd_confirm sudo apt-get --yes --force-yes install libprotobuf-dev python-protobuf;

header "Installing Sleuthkit and Pytsk"
run_cmd_confirm sudo apt-get --yes remove libtsk3* sleuthkit
run_cmd_confirm sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${SLEUTHKIT_DEB} ${DEB_DEPENDENCIES_DIR}/${PYTSK_DEB};

header "Installing Mongodb"
run_cmd_confirm sudo apt-get --yes --force-yes install mongodb python-pymongo;
sudo service mongodb start 2>/dev/null

header "Installing Rekall"
run_cmd_confirm sudo pip install rekall --upgrade --pre

header "Installing psutil via pip"
run_cmd_confirm sudo apt-get --yes remove python-psutil;
run_cmd_confirm sudo pip install psutil --upgrade

header "Installing Selenium test framework for Tests"
run_cmd_confirm sudo easy_install selenium


header "Checking Django version is > 1.4 and fixing up"
# We need 1.4, 12.04 ships with 1.3
DJANGO_VERSION=`dpkg-query -W python-django | cut -f 2`
if [[ "$DJANGO_VERSION" == 1.3* ]]; then
  echo "Unsupported Django version ${DJANGO_VERSION}. Upgrading with pip."
  run_cmd_confirm sudo apt-get --yes remove python-django
  run_cmd_confirm sudo easy_install django
fi


header "Installing GRR from prebuilt package"
SERVER_DEB=$(basename ${SERVER_DEB_URL});
if [ $GRR_LOCAL_TEST = 0 ]; then
  run_cmd_confirm wget --no-verbose ${SERVER_DEB_URL} -O ${SERVER_DEB};
  run_cmd_confirm sudo dpkg -i ${SERVER_DEB};
else
  run_cmd_confirm sudo dpkg -i ${SERVER_DEB};
fi

header "Initialize the configuration, building clients and setting options."
run_cmd_confirm sudo grr_config_updater initialize

header "Enable grr-single-server to start automatically on boot"
SERVER_DEFAULT=/etc/default/grr-single-server
run_cmd_confirm sudo sed -i 's/START=\"no\"/START=\"yes\"/' ${SERVER_DEFAULT};

header "Starting up the service"
sudo initctl status grr-single-server | grep "running"
IS_RUNNING=$?
if [ $IS_RUNNING = 0 ]; then
  run_cmd_confirm sudo service grr-single-server stop
fi
run_cmd_confirm sudo service grr-single-server start

HOSTNAME=`hostname`
echo "############################################################################################"
echo "Install complete. Congratulations. Point your browser at http://${HOSTNAME}:8000"
echo "############################################################################################"
echo ""
