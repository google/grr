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

PREFIX=/usr

# Allow PYTHONPATH to be set externally, need to check if its "" as well as this
# is valid here.
if [ -n "${PYTHONPATH-x}" ];
then
  PYTHONPATH=${PREFIX}/share;
fi

CONFIG_UPDATER=${PREFIX}/bin/grr_config_updater.py

echo "#########################################################################"
echo "###   Windows Client Builds"
echo "#########################################################################"

#### Notes
# The Windows clients get built with an injected script to make them one
# click to install. This requires a bit of work to get right with packing
# so this script automates the process.


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
CLIENT_BASE_DIR_32=$CLIENT_TEMPLATE_DIR/win32
CLIENT_BASE_DIR_64=$CLIENT_TEMPLATE_DIR/win64
SFX_DIR=$CLIENT_TEMPLATE_DIR/unzipsfx/
CLIENT_OUT_DIR=$CLIENT_DIR/installers
INSTALLER_DIR=$SCRIPTS_DIR



echo "Repacking 32 bit Windows client"

echo "Finding latest version"

VERSION=`ls $CLIENT_BASE_DIR_32 | sort -n | tail -n 1`

if [ "$VERSION" == "" ]; then
  echo "No 32 bit client template found."
else
  echo "Will use $VERSION"

  CLIENT_DIR_32=$CLIENT_BASE_DIR_32/$VERSION

  PYTHONPATH=${PYTHONPATH} python $INSTALLER_DIR/inject_keys.py \
    --type vbs \
    --ca_cert $KEYDIR/ca.pem \
    --driver_key $KEYDIR/driver_sign_pub.pem \
    --exe_key $KEYDIR/exe_sign_pub.pem \
    --installer_template $SCRIPTS_DIR/installer.vbs.template \
    --client_dir $CLIENT_DIR_32 \
    --package_build 32 \
    --location $LOCATION \
    --agent_version $VERSION

  if [ "$?" -eq "1" ]; then
    echo "################ ERROR ERROR ERROR ######################";
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

  WIN32_OUT=$CLIENT_OUT_DIR/grr-installer-win-$VERSION-32.exe;
  echo "Build successfull! Your 32 bit client installer has been placed in $WIN32_OUT"
fi;

echo "Repacking 64 bit Windows client"

echo "Finding latest version"

VERSION=`ls $CLIENT_BASE_DIR_64 | sort | tail -n 1`

if [ "$VERSION" == "" ]; then
  echo "No 64 bit client template found."
else
  echo "Will use $VERSION"

  CLIENT_DIR_64=$CLIENT_BASE_DIR_64/$VERSION

  PYTHONPATH=${PYTHONPATH} python $INSTALLER_DIR/inject_keys.py \
    --type vbs \
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

  WIN64_OUT=$CLIENT_OUT_DIR/grr-installer-win-$VERSION-64.exe;
  echo "Build successfull! Your 64 bit client installer has been placed in $WIN64_OUT"
fi

echo "#########################################################################"
echo "###   OSX Client Builds"
echo "#########################################################################"

#### Notes
# The OSX client currently doesn't have a config injector so we package it
# on its own. To install the user will have to install the package, and then
# drop the correct grr.ini into place in /etc/ so it will work.

CLIENT_DIR=$GRR_PATH/executables/osx
CLIENT_TEMPLATE_DIR=$CLIENT_DIR/templates
CLIENT_OUT_DIR=$CLIENT_DIR/installers

echo "Repacking OSX client"
echo "Finding latest version"
VERSION=`ls $CLIENT_TEMPLATE_DIR | sort -n | tail -n 1`

if [ "$VERSION" == "" ]; then
  echo "No osx client template found."
  exit -1
fi

echo "Will use $VERSION"

PYTHONPATH=${PYTHONPATH} python $INSTALLER_DIR/inject_keys.py \
  --type ini \
  --ca_cert $KEYDIR/ca.pem \
  --driver_key $KEYDIR/driver_sign_pub.pem \
  --exe_key $KEYDIR/exe_sign_pub.pem \
  --installer_template $SCRIPTS_DIR/grr.ini.template \
  --client_dir $CLIENT_OUT_DIR \
  --location $LOCATION \
  --agent_version $VERSION;

# Copy the DMG out to the installer directory where the grr.ini is.
OSX_OUT=${CLIENT_OUT_DIR}/GRR-${VERSION}.dmg;
OSX_INI=${CLIENT_OUT_DIR}/grr.ini;
cp $CLIENT_DIR/templates/${VERSION}/GRR.dmg ${OSX_OUT};
echo "Build successful! Your OSX installer and ini have been placed in $CLIENT_OUT_DIR"


echo "#########################################################################"
echo "###   Linux Client Builds"
echo "###         (no real support yet, just build the ini)"
echo "#########################################################################"

CLIENT_DIR=$GRR_PATH/executables/linux
CLIENT_OUT_DIR=$CLIENT_DIR/installers

mkdir -p $CLIENT_OUT_DIR

PYTHONPATH=${PYTHONPATH} python $INSTALLER_DIR/inject_keys.py \
  --type ini \
  --ca_cert $KEYDIR/ca.pem \
  --driver_key $KEYDIR/driver_sign_pub.pem \
  --exe_key $KEYDIR/exe_sign_pub.pem \
  --installer_template $SCRIPTS_DIR/grr.ini.template \
  --client_dir $CLIENT_OUT_DIR \
  --location $LOCATION \
  --agent_version $VERSION;

LINUX_INI=${CLIENT_OUT_DIR}/grr.ini;

echo "Build successful! Your Linuxini has been placed in $CLIENT_OUT_DIR"


echo "#########################################################################"
echo "###   Uploading built agents to the database"
echo "#########################################################################"


${CONFIG_UPDATER} --action=RAWUPLOAD --file=${OSX_OUT} \
  --upload_name=$(basename ${OSX_OUT}) \
  --aff4_path=/config/executables/osx/installers;

${CONFIG_UPDATER} --action=RAWUPLOAD --file=${OSX_INI} \
  --upload_name=$(basename ${OSX_INI}) \
  --aff4_path=/config/executables/osx/installers;

${CONFIG_UPDATER} --action=RAWUPLOAD --file=${LINUX_INI} \
  --upload_name=$(basename ${LINUX_INI}) \
  --aff4_path=/config/executables/linux/installers;

${CONFIG_UPDATER} --action=RAWUPLOAD \
  --file=${WIN64_OUT} \
  --upload_name=$(basename ${WIN64_OUT}) \
  --aff4_path=/config/executables/windows/installers;

${CONFIG_UPDATER} --action=RAWUPLOAD \
  --file=${WIN32_OUT} \
  --upload_name=$(basename ${WIN32_OUT}) \
  --aff4_path=/config/executables/windows/installers;

