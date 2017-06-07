#!/bin/bash

# Install dependencies.
sudo yum -y update
echo "Installing epel-release."
sudo yum -y install epel-release
sudo yum -y update
echo "Installing dependencies and building blocks."
sudo yum -y install make automake gcc gcc-c++ kernel-devel libtool swig glibc-devel git perl libffi-devel
sudo yum -y install wget prelink python-devel libxml2-devel libxml++-devel openssl-devel debbuild
sudo yum -y install python-pip

# Install Python 2.7.12 from source.
echo "Installing Python 2.7.12"
cd /usr/src
sudo wget https://www.python.org/ftp/python/2.7.12/Python-2.7.12.tgz
sudo tar xzf Python-2.7.12.tgz
cd Python-2.7.12
./configure
sudo make install
echo "What version of Python are we running now?"
python -V

# Move to installing users home directory.
echo "Returning home."
cd ~/
echo "We are now here:"
pwd

# Install our python dependencies.
sudo pip install --upgrade pip
sudo pip install virtualenv

echo "No more sudo requests."

# Create GRR's virtualenv
virtualenv GRR_ENV
source GRR_ENV/bin/activate

# GRR
echo "Installing GRR server now."
pip install grr-response-server

echo "Installing GRR client templates."
pip install -f https://storage.googleapis.com/releases.grr-response.com/index.html grr-response-templates

echo "Prepare for GRR Server initialization."
grr_config_updater initialize

# Don't forget
echo "Build complete."
echo "Run 'source GRR_ENV/bin/activate' before running 'grr_server --help'."
echo "Also, to reconfigure do 'grr_config_updater initialize'."
