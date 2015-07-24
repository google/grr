#!/bin/bash
#
# Script to install GRR from scratch on an Ubuntu 12.04, 12.10 or 13.04 system.
#
# By default this will install into /usr and set the config in
# /etc/grr/
#
PREFIX=/usr

# If true, do an apt-get upgrade
: ${UPGRADE:=true}

# Variables to control the install versions etc. Made for changing this to
# support other platforms more easily.
PLAT=amd64
INSTALL_DIR=${PREFIX}/share/grr

GRR_STABLE_VERSION=0.3.0-7
GRR_TEST_VERSION=
SERVER_DEB_STABLE_BASE_URL=https://googledrive.com/host/0B1wsLqFoT7i2c3F0ZmI1RDJlUEU/grr-server_
SERVER_DEB_TEST_BASE_URL=https://googledrive.com/host/0B1wsLqFoT7i2c3F0ZmI1RDJlUEU/test-grr-server_

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

# Variable to store if the user has answered "Yes to All"
ALL_YES=0;

# If true only install build dependencies. GRR itself and the database won't be
# installed.
BUILD_DEPS_ONLY=0;

# Use local deb, for testing
GRR_LOCAL_TEST=0

# Use the GRR test version
GRR_TESTING=0;

OPTIND=1
while getopts "h?ltdy" opt; do
    case "$opt" in
    h|\?)
        echo "Usage: ./install_script_ubuntu.sh [OPTIONS]"
        echo " -l Test locally (no download), get deb from current path"
        echo " -t Install the GRR beta testing version"
        echo " -d Only install build dependencies"
        echo " -y Don't prompt, i.e. answer yes to everything"
        exit 0
        ;;
    l)  GRR_LOCAL_TEST=1
        ;;
    t)  GRR_TESTING=1;
        ;;
    d)  BUILD_DEPS_ONLY=1;
        ;;
    y)  ALL_YES=1;
        ;;
    esac
done

shift $((OPTIND-1))
[ "$1" = "--" ] && shift

echo "Running with GRR_LOCAL_TEST=${GRR_LOCAL_TEST}, GRR_TESTING=${GRR_TESTING}, BUILD_DEPS_ONLY=${BUILD_DEPS_ONLY}, ALL_YES=${ALL_YES}"

if [ ${GRR_TESTING} = 0 ];
then
  SERVER_DEB_URL=${SERVER_DEB_STABLE_BASE_URL}${GRR_STABLE_VERSION}_${PLAT}.deb
else
  echo "#########################################"
  echo "#### Running with Beta test versions ####"
  echo "#########################################"
  SERVER_DEB_URL=${SERVER_DEB_TEST_BASE_URL}${GRR_TEST_VERSION}_${PLAT}.deb
fi

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

header "Increase our filehandle limit (for SQLite datastore)."
run_cmd_confirm echo "fs.file-max = 1048576" >> /etc/sysctl.conf
run_cmd_confirm sysctl -p
echo "Filehandle limit now: $(cat /proc/sys/fs/file-max)"

header "Updating APT and Installing dependencies"
run_cmd_confirm apt-get --yes update;
if $UPGRADE; then
  run_cmd_confirm apt-get --yes upgrade;
fi

header "Adding launchpad.net/~gift PPA for m2crypto pytsk dependencies."
run_cmd_confirm apt-get install -y software-properties-common
run_cmd_confirm add-apt-repository ppa:gift/dev -y
run_cmd_confirm apt-get update -q

header "Installing dependencies."
run_cmd_confirm apt-get --force-yes --yes install \
  apache2-utils \
  build-essential \
  debhelper \
  dpkg-dev \
  ipython \
  libprotobuf-dev \
  ncurses-dev \
  prelink \
  protobuf-compiler \
  python-dateutil \
  python-ipaddr \
  python-m2crypto \
  python-matplotlib \
  python-mock \
  python-mox \
  python-pandas \
  python-pip \
  python-protobuf \
  python-setuptools \
  python-support \
  pytsk3 \
  python-yaml \
  python-werkzeug \
  rpm \
  sleuthkit \
  wget \
  zip

# Fail silently if python-dev or libpython-dev is not available in the apt repo
# python-dev is for Ubuntu version < 12.10 and libpython-dev is for > 12.04
apt-get --force-yes --yes install python-dev 2>/dev/null
apt-get --force-yes --yes install libpython-dev 2>/dev/null

run_cmd_confirm pip install pip --upgrade

header "Installing Rekall"
INSTALL_REKALL=0
if [ ${ALL_YES} = 0 ]; then
  echo ""
  read -p "Run pip install rekall --upgrade [Y/n/a]? " REPLY
  case $REPLY in
    y|Y|'') INSTALL_REKALL=1;;
    a|A) echo "Answering yes from now on"; ALL_YES=1; INSTALL_REKALL=1;;
  esac
else
  INSTALL_REKALL=1
fi

if [ ${INSTALL_REKALL} = 1 ]; then
  pip install rekall --upgrade
  RETVAL=$?
  if [ $RETVAL -ne 0 ]; then
    exit_fail pip install rekall --upgrade;
  fi
fi

header "Installing psutil via pip"
run_cmd_confirm apt-get --yes remove python-psutil;
run_cmd_confirm pip install psutil --upgrade

header "Installing Selenium test framework for Tests"
run_cmd_confirm easy_install selenium

header "Installing correct Django version."
# We support everything from 1.4 to 1.6, 12.04 ships with 1.3. This is only
# necessary for server 0.3.0-2, remove the requirement for 1.6 once we upgrade.
run_cmd_confirm apt-get --yes remove python-django
run_cmd_confirm pip install django==1.6

if [ $BUILD_DEPS_ONLY = 1 ]; then
  echo "#######################################"
  echo "Finished installing build dependencies."
  echo "#######################################"
  exit 0
fi

header "Installing GRR from prebuilt package"
SERVER_DEB=$(basename ${SERVER_DEB_URL});
if [ $GRR_LOCAL_TEST = 0 ]; then
  run_cmd_confirm wget --no-verbose ${SERVER_DEB_URL} -O ${SERVER_DEB};
  run_cmd_confirm dpkg -i ${SERVER_DEB};
else
  run_cmd_confirm dpkg -i ${SERVER_DEB};
fi

header "Initialize the configuration, building clients and setting options."
run_cmd_confirm grr_config_updater initialize

header "Enable grr services to start automatically on boot"

for SERVER in grr-http-server grr-worker grr-ui
do
  SERVER_DEFAULT=/etc/default/${SERVER}
  # The package has START=no to enable users installing distributed components
  # to selectively enable what they want on each machine. Here we want them all
  # running.
  run_cmd_confirm sed -i 's/START=\"no\"/START=\"yes\"/' ${SERVER_DEFAULT};

  header "Starting ${SERVER}"

  initctl status ${SERVER} | grep "running"
  IS_RUNNING=$?
  if [ $IS_RUNNING = 0 ]; then
    run_cmd_confirm service ${SERVER} stop
  fi
  run_cmd_confirm service ${SERVER} start
done

HOSTNAME=`hostname`
echo "############################################################################################"
echo "Install complete. Congratulations. Point your browser at http://${HOSTNAME}:8000"
echo "############################################################################################"
echo ""
