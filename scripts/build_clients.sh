#!/bin/bash
#
# Script to generate and package working GRR Agents that require no options
# when run.
#
# This script injects the configuration into a working executable to ease
# deployment. This configuration uses a number of cryptographic keys, they
# will be sourced from /etc/grr/keys by default. You can override that path by
# setting the KEYDIR environment variable.
# export KEYDIR=/tmp/keys
#

# Allow KEYDIR to be overridden by environment variable.
if [ -z "${KEYDIR}" ];
then
  KEYDIR="/etc/grr/keys";
fi
echo "Using ${KEYDIR} for keys"

# Allow PYTHONPATH to be set externally, need to check if its "" as well as this
# is valid here.
if [ -n "${PYTHONPATH-x}" ];
then
  PYTHONPATH="/usr/share";
fi



# Set this to OUT="&1" for debugging.
OUT="/dev/null"
OUT="&1"

# Generate the keys if they are not there.
export KEYDIR
SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ${SCRIPTS_DIR}/generate_keys.sh

echo "Injecting keys into install.vbs"

echo "Please enter the server location your clients should connect to (example: http://grrserver.com:8080/control)"


# Allow GRR_SERVER_URL to be set externally.
if [ -z "${GRR_SERVER_URL}" ];
then
  read LOCATION
else
  LOCATION="${GRR_SERVER_URL}";
fi

if [ "$LOCATION" == "" ]; then
  echo "Need a location. Exiting."
  exit
fi;

GRR_PATH=$(dirname ${SCRIPTS_DIR})
CLIENT_DIR=$GRR_PATH/executables/windows
CLIENT_TEMPLATE_DIR=$CLIENT_DIR/templates
CLIENT_BASE_DIR_32=$CLIENT_TEMPLATE_DIR/win32/
CLIENT_BASE_DIR_64=$CLIENT_TEMPLATE_DIR/win64/
SFX_DIR=$CLIENT_TEMPLATE_DIR/unzipsfx/
CLIENT_OUT_DIR=$CLIENT_DIR/installers
INSTALLER_DIR=$SCRIPTS_DIR

echo "Repacking 32 bit client"

echo "Finding latest version"

VERSION=`ls $CLIENT_BASE_DIR_32 | sort -n | tail -n 1`

if [ "$VERSION" == "" ]; then
  echo "No 32 bit client template found."
else
  echo "Will use $VERSION"

  CLIENT_DIR_32=$CLIENT_BASE_DIR_32/$VERSION

  PYTHONPATH=${PYTHONPATH} python $INSTALLER_DIR/inject_keys.py \
    --ca_cert $KEYDIR/ca.pem \
    --driver_key $KEYDIR/driver_sign_pub.pem \
    --exe_key $KEYDIR/exe_sign_pub.pem \
    --installer_template $SCRIPTS_DIR/installer.vbs.template \
    --client_dir $CLIENT_DIR_32 \
    --package_build 32 \
    --location $LOCATION \
    --agent_version $VERSION

  if [ "$?" -eq "1" ]; then
    exit
  fi;

  echo "Compressing compiled grr directory from $CLIENT_DIR_32"
  mkdir -p $CLIENT_OUT_DIR
  echo \$AUTORUN\$\>wscript installer.vbs | zip -zj $CLIENT_OUT_DIR/grr32.zip $CLIENT_DIR_32/* >$OUT
  if [ "$?" -eq "1" ]; then
    echo "Failed to zip"
  fi;

  echo "Adding self extractor to $CLIENT_OUT_DIR/grr32.zip"
  cat $SFX_DIR/unzipsfx-32.exe $CLIENT_OUT_DIR/grr32.zip >$CLIENT_OUT_DIR/grr-installer-win-$VERSION-32.exe

  echo "All done, cleaning up"
  rm $CLIENT_OUT_DIR/grr32.zip

  echo "Build successfull! Your 32 bit client installer has been placed in $CLIENT_OUT_DIR"
fi;

echo "Repacking 64 bit client"

echo "Finding latest version"

VERSION=`ls $CLIENT_BASE_DIR_64 | sort | tail -n 1`

if [ "$VERSION" == "" ]; then
  echo "No 64 bit client template found."
else
  echo "Will use $VERSION"

  CLIENT_DIR_64=$CLIENT_BASE_DIR_64/$VERSION

  PYTHONPATH=${PYTHONPATH} python $INSTALLER_DIR/inject_keys.py \
    --ca_cert $KEYDIR/ca.pem \
    --driver_key $KEYDIR/driver_sign_pub.pem \
    --exe_key $KEYDIR/exe_sign_pub.pem \
    --installer_template $SCRIPTS_DIR/installer.vbs.template \
    --client_dir $CLIENT_DIR_64 \
    --package_build 64 \
    --location $LOCATION \
    --agent_version $VERSION

  if [ "$?" -eq "1" ]; then
    exit
  fi;

  echo "Compressing compiled grr directory from $CLIENT_DIR_64"
  mkdir -p $CLIENT_OUT_DIR
  echo \$AUTORUN\$\>wscript installer.vbs | zip -zj $CLIENT_OUT_DIR/grr64.zip $CLIENT_DIR_64/* >$OUT
  if [ "$?" -eq "1" ]; then
    echo "Failed to zip"
  fi;

  echo "Adding self extractor to $CLIENT_OUT_DIR/grr64.zip"
  cat $SFX_DIR/unzipsfx-64.exe $CLIENT_OUT_DIR/grr64.zip >$CLIENT_OUT_DIR/grr-installer-win-$VERSION-64.exe

  echo "All done, cleaning up"
  rm $CLIENT_OUT_DIR/grr64.zip

  echo "Build successfull! Your 64 bit client installer has been placed in $CLIENT_OUT_DIR"

fi;

