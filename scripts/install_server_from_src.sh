#!/bin/bash

# This script will install GRR server dependencies and components from source.

# It is called in four ways:
# config/debian/dpkg_server/rules
# Dockerfile
# Vagrantfile for grr_server_dev
# directly when installing GRR from src

set -e

DOCKER=false;
GRR_INSTALL=true;
UBUNTU_DEPS_INSTALL=true;
PYTHON_DEPS_INSTALL=false;
DOWNLOAD_CLIENT_TEMPLATES=true;
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
        echo " -l Install using symlinks to GRR source for installed files"
        echo " -p Install using only Python packages (Skip Ubuntu package installs)"
        echo " -s Setup only. Do not install any dependencies, GRR, or client templates"
        echo " -d Custom settings for running from GRR repo Dockerfile."
        exit 0
        ;;
    r)  SRC_DIR=$OPTARG;
        ;;
    i)  INSTALL_PREFIX=$OPTARG;
        ;;
    l)  INSTALL_BIN="ln";
        INSTALL_OPTS="-snf";
        ;;
    p)  UBUNTU_DEPS_INSTALL=false;
        PYTHON_DEPS_INSTALL=true;
        ;;
    s)  UBUNTU_DEPS_INSTALL=false;
        GRR_INSTALL=false;
        PYTHON_DEPS_INSTALL=false;
        DOWNLOAD_CLIENT_TEMPLATES=false;
        ;;
    d)  DOCKER=true;
        UBUNTU_DEPS_INSTALL=false;
        DOWNLOAD_CLIENT_TEMPLATES=false;
        ;;
    esac
done

shift $((OPTIND-1))
[ "$1" = "--" ] && shift

INSTALL_CMD="$INSTALL_BIN $INSTALL_OPTS"
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit 1
fi

cd "$SRC_DIR"
CURDIR=$(basename "$PWD")
if [[ "$CURDIR" != "grr" ]]; then
  echo "Please run from the grr source directory or provide a valid path to the source directory with -s"
  exit 2
fi

if $UBUNTU_DEPS_INSTALL; then
  header "Installing GRR Dependencies"
  # Install GRR dependencies
  "$SRC_DIR/scripts/install_script_ubuntu.sh" -dy -r "$SRC_DIR/requirements.txt"
fi

if $PYTHON_DEPS_INSTALL ;then
  header "Installing GRR Python Dependencies"
  pip install -r "$SRC_DIR/requirements.txt"
fi

if $GRR_INSTALL; then
  header "Removing Any Old GRR Installs and Install GRR From Source"
  # Remove any old installation and install GRR
  rm -rf /usr/lib/python2.7/dist-packages/grr
  rm -rf /usr/local/lib/python2.7/dist-packages/grr
  rm -rf /usr/lib/python2.7/site-packages/grr
  rm -rf /usr/local/lib/python2.7/site-packages/grr
  python setup.py build
  python setup.py install
fi

mkdir -p "$INSTALL_PREFIX/usr/sbin"

header "Install Configuration Files"
# Set up default configuration
mkdir -p "$INSTALL_PREFIX/etc/grr"

$INSTALL_CMD "$SRC_DIR/config/grr-server.yaml" "$INSTALL_PREFIX/etc/grr/grr-server.yaml"

# Set up upstart scripts
mkdir -p "$INSTALL_PREFIX/etc/default"
mkdir -p "$INSTALL_PREFIX/etc/init"

install -p -m644 "$SRC_DIR"/config/upstart/default/grr-* "$INSTALL_PREFIX/etc/default"

for init_script in "$SRC_DIR"/config/upstart/grr-*; do
  init_script_fn=$(basename "${init_script}")
  if [ "$init_script_fn" != 'grr-client.conf' ]; then
    $INSTALL_CMD "${init_script}" "$INSTALL_PREFIX/etc/init/${init_script_fn}"
  fi
done

# Reload Upstart configuration for newly installed services
initctl reload-configuration

# Generate all the template directories and download client templates.
for template in darwin linux windows; do
  mkdir -p "$SRC_DIR/executables/${template}/templates/"
  mkdir -p "$SRC_DIR/executables/${template}/installers/"
  mkdir -p "$SRC_DIR/executables/${template}/config/"
done

if $DOWNLOAD_CLIENT_TEMPLATES; then
  header "Downloading Client Templates"
  "$SRC_DIR/scripts/download_client_templates.sh" -d "$SRC_DIR"
fi

# When run from docker we don't need this section because we've already
# installed the client templates and put the whole src tree under /usr/share/grr

if ! $DOCKER; then
  header "Setting up ${INSTALL_PREFIX}/usr/share/grr/"
  # Set up grr-server shared directories and files
  mkdir -p "$INSTALL_PREFIX/usr/share/grr"

  # For a dev environment link the share directories to the source directory
  if [ $INSTALL_BIN == "ln" ]; then
    $INSTALL_CMD "$SRC_DIR/executables/" "$INSTALL_PREFIX/usr/share/grr/executables"
    $INSTALL_CMD "$SRC_DIR/scripts/" "$INSTALL_PREFIX/usr/share/grr/scripts"
    $INSTALL_CMD "$SRC_DIR/binaries/" "$INSTALL_PREFIX/usr/share/grr/binaries"
  else
  # Otherwise copy the files from the source directory to the share directories
    # Copy the templates from the source dir
    for template in executables/*/templates/{grr,GRR}_*; do
      install -p -m755 -D "${template}" "$INSTALL_PREFIX/usr/share/grr/${template}"
    done

    for zipfix in executables/windows/templates/unzipsfx/*.*; do
      install -p -m755 -D "${zipfix}" "$INSTALL_PREFIX/usr/share/grr/${zipfix}"
    done

    # Copy the scripts from the source dir
    for script in scripts/*.sh; do
      install -p -m755 -D "${script}" "$INSTALL_PREFIX/usr/share/grr/${script}"
    done

    #copy the binaries from the source dir
    for binary in binaries/*.*; do
      install -p -m755 -D "${binary}" "$INSTALL_PREFIX/usr/share/grr/${binary}"
    done
  fi
fi

# Set up log directory
mkdir -p "$INSTALL_PREFIX"/var/log/grr

echo "#################################################################"
echo "Install complete"
echo ""
if [ $INSTALL_BIN == "ln" ]; then
echo "GRR source is located in ${SRC_DIR}"
echo ""
echo "Run unit tests:"
echo "   ${SRC_DIR}/run_tests.sh"
echo ""
fi
echo "Next steps if new install:"
echo "   (Optional) Install/Configure MySQL"
echo "   sudo grr_config_updater initialize"
echo "   source ${INSTALL_PREFIX}/usr/share/grr/scripts/shell_helpers.sh"
echo "   grr_enable_all"
echo ""
echo "If upgrading see:"
echo "https://github.com/google/grr-doc/blob/master/releasenotes.adoc"
echo "#################################################################"
