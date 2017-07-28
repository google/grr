#!/bin/bash

set -e

yum install -y \
  emacs \
  epel-release \
  python-devel \
  wget \
  which \
  java-1.8.0-openjdk \
  libffi-devel \
  openssl-devel \
  zip \
  git \
  gcc \
  gcc-c++ \
  redhat-rpm-config \
  rpm-build \
  rpm-sign

yum install -y python-pip
pip install --upgrade pip virtualenv
