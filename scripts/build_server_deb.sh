#!/bin/bash
# Trivial script to build the server deb from a source tree.

CURDIR=$(basename $PWD)
if [[ "$CURDIR" != "grr" || ! -e "setup.py" ]]; then
  echo "Please run from the grr source directory"
  exit 1
fi

sudo rm -rf ./debian
sudo cp -r config/debian/dpkg_server ./debian
sudo dpkg-buildpackage -rfakeroot
