#!/bin/bash
# Trivial script to build the server deb from a source tree.

CURDIR=$(basename $PWD)
if [[ "$CURDIR" != "grr" || ! -e "setup.py" ]]; then
  echo "Please run from the grr source directory"
  exit 1
fi

SOURCE=$PWD

# Build the deb in a standalone directory outside the package tree.
mkdir -p build
cd build
rm -rf ./debian ./build ./dist
cp -r "$SOURCE/grr/config/debian/dpkg_server" ./debian
cp debian/setup.py .

# Internet access is required to download the latest artifacts
dpkg-buildpackage -rfakeroot

# Tear down the build directory.
cd -
rm -rf build
