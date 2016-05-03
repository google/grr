#!/bin/bash
# Trivial script to build the server deb from a source tree.

set -e

CURDIR=$(basename $PWD)
if [[ "$CURDIR" != "grr" || ! -e "setup.py" ]]; then
  echo "Please run from the grr source directory"
  exit 1
fi

SOURCE=$PWD

# Build the deb in a standalone directory outside the package tree.
builddir=$(mktemp -d --suffix="grr-build")
cd "$builddir"

# We need the whole source in this directory because pip is going to copy it to
# yet another tempdir to make a wheel.
cp -r "$SOURCE" .

rm -rf ./debian ./build ./dist
cp -r "$SOURCE/install_data/debian/dpkg_server" ./debian
cp debian/setup.py .

# Internet access is required to download the latest artifacts
dpkg-buildpackage -rfakeroot

# dpkg output is ".." and it doesn't seem like there's a good way to change
# that. So pickup the package files from /tmp
mkdir -p /output
mv /tmp/grr-server* /output/

# Tear down the build directory.
cd -
rm -rf "$builddir"

echo "Complete. Package files are in /output"
