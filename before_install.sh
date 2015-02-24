#!/bin/bash
PROTO_PACKAGES=(libprotobuf9_2.6.1-1ppa1~precise_amd64.deb libprotobuf-lite9_2.6.1-1ppa1~precise_amd64.deb libprotobuf-dev_2.6.1-1ppa1~precise_amd64.deb libprotobuf-java_2.6.1-1ppa1~precise_all.deb libprotoc9_2.6.1-1ppa1~precise_amd64.deb libprotoc-dev_2.6.1-1ppa1~precise_amd64.deb protobuf-compiler_2.6.1-1ppa1~precise_amd64.deb python-protobuf_2.6.1-1ppa1~precise_amd64.deb)

mkdir protobuf-debs
cd protobuf-debs

echo "Installing protobuf debs"
for i in ${PROTO_PACKAGES[@]}; do
  echo "Downloading custom package $i"
  wget https://dionyziz.com/protobuf-debs/$i
  echo "Installing $i"
  sudo dpkg -i $i
done
cd ..
echo "Protobuf debs installed"

sudo apt-get install python-software-properties
sudo add-apt-repository ppa:kristinn-l/plaso-dev -y
sudo apt-get update -q
sudo apt-get install m2crypto python-support libdistorm64-1 libdistorm64-dev python-psutil pytsk3 ncurses-dev python-pip

PLAT=amd64
DEB_DEPENDENCIES_URL=https://googledrive.com/host/0B1wsLqFoT7i2aW5mWXNDX1NtTnc/ubuntu-12.04-${PLAT}-debs.tar.gz
DEB_DEPENDENCIES_DIR=ubuntu-12.04-${PLAT}-debs
SLEUTHKIT_DEB=sleuthkit-lib_3.2.3-1_${PLAT}.deb

DEB_DEPENDENCIES_TARBALL=$(basename ${DEB_DEPENDENCIES_URL})
wget --no-verbose ${DEB_DEPENDENCIES_URL} -O ${DEB_DEPENDENCIES_TARBALL}
tar zxfv ${DEB_DEPENDENCIES_TARBALL}
sudo dpkg -i ${DEB_DEPENDENCIES_DIR}/${SLEUTHKIT_DEB}
