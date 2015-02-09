#!/bin/bash
pip install -r requirements.txt
sudo apt-get install python-protobuf libprotoc-dev protobuf-compiler m2crypto python-support libdistorm64-1 libdistorm64-dev python-psutil pytsk3 ncurses-dev python-pip

PLAT=amd64
DEB_DEPENDENCIES_URL=https://googledrive.com/host/0B1wsLqFoT7i2aW5mWXNDX1NtTnc/ubuntu-12.04-${PLAT}-debs.tar.gz
DEB_DEPENDENCIES_DIR=ubuntu-12.04-${PLAT}-debs
SLEUTHKIT_DEB=sleuthkit-lib_3.2.3-1_${PLAT}.deb

DEB_DEPENDENCIES_TARBALL=$(basename ${DEB_DEPENDENCIES_URL})
wget --no-verbose ${DEB_DEPENDENCIES_URL} -O ${DEB_DEPENDENCIES_TARBALL}
tar zxfv ${DEB_DEPENDENCIES_TARBALL}
sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${SLEUTHKIT_DEB}

echo "Compiling proto files..."
echo "protoc version:"
protoc --version
cd proto
echo "Running make in proto dir..."
pwd
make
cd ..

echo "Compiling artifact files..."
cd artifacts
echo "Running make in artifacts dir..."
pwd
make
cd ..
