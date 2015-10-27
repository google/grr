#!/bin/bash

# This script will install GRR server components from source. It assumes
# all dependencies have already been fulfilled by running
# scripts/install_script_ubuntu.sh or manual installation.

# It is called in three ways:
# config/debian/dpkg_server/rules
# Dockerfile
# directly when installing GRR from src

set -e

: ${INSTALL_PREFIX:=""}
: ${DOWNLOAD_CLIENT_TEMPLATES:=true}
: ${PYTHON_INSTALL:=true}
: ${DOCKER:=false}

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit 1
fi

CURDIR=$(basename $PWD)
if [[ "$CURDIR" != "grr" ]]; then
  echo "Please run from the grr source directory"
  exit 2
fi

if $PYTHON_INSTALL; then
  # Remove any old installation and install GRR
  rm -rf /usr/lib/python2.7/dist-packages/grr
  python setup.py build
  python setup.py install
fi

mkdir -p $INSTALL_PREFIX/usr/sbin
# Set up default configuration
mkdir -p $INSTALL_PREFIX/etc/grr
install -p -m644 config/grr-server.yaml $INSTALL_PREFIX/etc/grr
# Set up upstart scripts
mkdir -p $INSTALL_PREFIX/etc/default
mkdir -p $INSTALL_PREFIX/etc/init
install -p -m644 config/upstart/default/grr-* $INSTALL_PREFIX/etc/default
install -p -m644 config/upstart/grr-* $INSTALL_PREFIX/etc/init
# Do not copy the client script across for the server package.
rm $INSTALL_PREFIX/etc/init/grr-client.conf

# Set up grr-server shared directories and files
mkdir -p $INSTALL_PREFIX/usr/share/grr/scripts
mkdir -p $INSTALL_PREFIX/usr/share/grr/binaries
mkdir -p $INSTALL_PREFIX/usr/share/grr/executables/windows/templates/unzipsfx/

# Generate all the template directories.
for template in darwin linux windows; do
  mkdir -p $INSTALL_PREFIX/usr/share/grr/executables/${template}/templates/
  mkdir -p $INSTALL_PREFIX/usr/share/grr/executables/${template}/installers/
  mkdir -p $INSTALL_PREFIX/usr/share/grr/executables/${template}/config/
done

# Make a copy of the default config so users can refer to it.
install -p -m644 -T config/grr-server.yaml $INSTALL_PREFIX/usr/share/grr/grr-server.yaml.default

if $DOWNLOAD_CLIENT_TEMPLATES; then
  scripts/download_client_templates.sh
fi

# When run from docker we don't need this section because we've already
# installed the client templates and put the whole src tree under /usr/share/grr
if ! $DOCKER; then
  install -p -m755 scripts/*sh $INSTALL_PREFIX/usr/share/grr/scripts/

  # Copy the templates from the current tree
  for template in executables/*/templates/{grr,GRR}_*; do install -p -m755 ${template} $INSTALL_PREFIX/usr/share/grr/$(dirname ${template}); done

  install -p -m755 executables/windows/templates/unzipsfx/*.* $INSTALL_PREFIX/usr/share/grr/executables/windows/templates/unzipsfx/

  install -p -m755 binaries/*.* $INSTALL_PREFIX/usr/share/grr/binaries/
fi

# Set up log directory
mkdir -p $INSTALL_PREFIX/var/log/grr

echo "#################################################################"
echo "Install complete"
echo ""
echo "Next steps if new install:"
echo "   sudo grr_config_updater initialize"
echo "   source scripts/shell_helpers.sh"
echo "   grr_enable_all"
echo ""
echo "If upgrading see:"
echo "https://github.com/google/grr-doc/blob/master/releasenotes.adoc"
echo "#################################################################"

