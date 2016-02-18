#!/bin/bash

# $Id: $
set -e

# TODO(user): we need to switch away from using drive to host these templates
# to something else that supports listing directories and fetching the contents.
# When using drive you need to reference the parent directory, which is version
# specific, and download each file explicitly. So these two strings will need to
# be updated for every new client template release.
CLIENT_TEMPLATE_DIRECTORY="https://googledrive.com/host/0B1wsLqFoT7i2VXBtSlJHRF9ycFU/"
CLIENT_TEMPLATE_VERSION="3.0.7.1"
DOWNLOAD_DIR="./"

while getopts "h?d:u:" opt; do
    case "$opt" in
    h|\?)
        echo "Usage: ./download_client_templates.sh [OPTIONS]"
        echo " -d [directory] Download to directory"
        echo " -u [url] URL to template files"
        echo " -v [version] Template version to download"
        exit 0
        ;;
    d)  DOWNLOAD_DIR=$OPTARG;
        ;;
    u)  CLIENT_TEMPLATE_DIRECTORY=$OPTARG;
        ;;
    v)  CLIENT_TEMPLATE_VERSION=$OPTARG;
        ;;
    esac
done

mkdir -p executables/darwin/templates/
mkdir -p executables/linux/templates/
mkdir -p executables/windows/templates/
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/darwin/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/grr_${CLIENT_TEMPLATE_VERSION}_amd64.pkg.xar"
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/linux/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/grr_${CLIENT_TEMPLATE_VERSION}_amd64.deb.zip"
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/linux/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/grr_${CLIENT_TEMPLATE_VERSION}_i386.deb.zip"
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/linux/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/grr_${CLIENT_TEMPLATE_VERSION}_amd64.rpm.zip"
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/linux/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/grr_${CLIENT_TEMPLATE_VERSION}_i386.rpm.zip"
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/windows/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/GRR_${CLIENT_TEMPLATE_VERSION}_amd64.exe.zip"
wget -N --quiet -P "${DOWNLOAD_DIR}/executables/windows/templates/" "${CLIENT_TEMPLATE_DIRECTORY}/GRR_${CLIENT_TEMPLATE_VERSION}_i386.exe.zip"
