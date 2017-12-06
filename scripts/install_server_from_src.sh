#!/bin/bash

# This script will install GRR server dependencies and components from source.
# It is called by install_data/debian/dpkg_server/rules when building the deb
# package.

set -x
set -e

INSTALL_PREFIX="";
INSTALL_BIN="install";
INSTALL_OPTS="-p -m644";
SRC_DIR=".";


function header()
{
  echo ""
  echo "##########################################################################################"
  echo "     ${*}";
  echo "##########################################################################################"
}

OPTIND=1
while getopts "h?lpsdr:i:" opt; do
    case "$opt" in
    h|\?)
        echo "Usage: ./install_server_from_src.sh [OPTIONS]"
        echo " -r Path to GRR repository files"
        echo " -i Install prefix path"
        exit 0
        ;;
    r)  SRC_DIR=$OPTARG;
        ;;
    i)  INSTALL_PREFIX=$OPTARG;
        ;;
    esac
done

shift $((OPTIND-1))
[ "$1" = "--" ] && shift

INSTALL_CMD="$INSTALL_BIN $INSTALL_OPTS"

# Turn these into absolute paths.
cd "$INSTALL_PREFIX"
INSTALL_PREFIX=$PWD
cd -

cd "$SRC_DIR"
SRC_DIR=$PWD
cd -

SRC_DIR_BASE=$(basename "$SRC_DIR")
if [[ "$SRC_DIR_BASE" != "grr" ]]; then
  echo "Please run from the grr source directory or provide a valid path to the source directory with -r"
  exit 2
fi

header "Install Configuration Files"
# Set up default configuration
mkdir -p "$INSTALL_PREFIX/etc/grr"

# When installed globally the config files are copied to the global
# configuration directory, except grr-server.yaml, which is effectively part of
# the code.
for f in $SRC_DIR/install_data/etc/*.yaml; do
  if [ "$f" != "$SRC_DIR/install_data/etc/grr-server.yaml" ]; then
    $INSTALL_CMD "$f" "$INSTALL_PREFIX/etc/grr/"
  fi
done

# Install all the script entry points in /usr/bin/.
mkdir -p "$INSTALL_PREFIX/usr/bin/"

LAUNCHER="$SRC_DIR/scripts/debian_launcher"
LAUNCHER_NO_EXTRA_ARGS="$SRC_DIR/scripts/debian_launcher_no_extra_args"

$INSTALL_CMD $LAUNCHER_NO_EXTRA_ARGS "$INSTALL_PREFIX/usr/bin/grr_api_shell"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_config_updater"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_console"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_server"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_fuse"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_end_to_end_tests"

# dh_installinit doesn't cater for systemd template files. The
# service target is installed by dh_installinit we just need to copy over the
# template.
$INSTALL_CMD "$SRC_DIR/debian/grr-server@.service" "$INSTALL_PREFIX/lib/systemd/system/"

# Set up log directory
mkdir -p "$INSTALL_PREFIX"/var/log/grr

header "Install Complete"
