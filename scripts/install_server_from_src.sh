#!/bin/bash

# This script will install GRR server dependencies and components from source.

# It is called in four ways:
# install_data/debian/dpkg_server/rules
# Dockerfile
# Vagrantfile for grr_server_dev
# directly when installing GRR from src

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
# configuration directory.
for f in "$SRC_DIR/install_data/etc/*.yaml"; do
  $INSTALL_CMD $f  "$INSTALL_PREFIX/etc/grr/"
done

# Install all the script entry points in /usr/bin/.
mkdir -p "$INSTALL_PREFIX/usr/bin/"

LAUNCHER="$SRC_DIR/scripts/debian_launcher"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_config_updater"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_console"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_server"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_export"
$INSTALL_CMD $LAUNCHER "$INSTALL_PREFIX/usr/bin/grr_fuse"

# Set up upstart scripts
mkdir -p "$INSTALL_PREFIX/etc/default"
mkdir -p "$INSTALL_PREFIX/etc/init"

$INSTALL_CMD "$SRC_DIR"/install_data/debian/dpkg_server/upstart/default/grr* "$INSTALL_PREFIX/etc/default"

for init_script in "$SRC_DIR"/install_data/debian/dpkg_server/upstart/grr-*; do
  $INSTALL_CMD "${init_script}" "$INSTALL_PREFIX/etc/init/"
done

# Set up log directory
mkdir -p "$INSTALL_PREFIX"/var/log/grr

echo "#################################################################"
echo "Install complete"
echo ""
echo "Next steps if new install:"
echo "   (Optional) Install/Configure MySQL"
echo "   sudo grr_config_updater initialize"
echo "   source ${INSTALL_PREFIX}/usr/share/grr/scripts/shell_helpers.sh"
echo "   grr_enable_all"
echo ""
echo "If upgrading see:"
echo "https://github.com/google/grr-doc/blob/master/releasenotes.adoc"
echo "#################################################################"
