# Docker file that builds a Centos 7 image with a recent version of
# Python installed.

FROM rockylinux:8.9

LABEL maintainer="grr-dev@googlegroups.com"

WORKDIR /tmp/grrdocker-scratch

# Install pre-requisites for building Python, as well as GRR prerequisites.
RUN yum update -y && yum install -y make zlib-devel bzip2-devel ncurses-devel \
  sqlite-devel readline-devel tk-devel gdbm-devel \
  xz-devel epel-release wget which java-1.8.0-openjdk \
  libffi-devel openssl-devel zip git gcc gcc-c++ redhat-rpm-config rpm-build \
  rpm-sign

# Install openssl11 for cryptography.
# Note: including openssl11-devel and openssl11-libs into the command above
# doesn't work (yum reports them as not found). This is likely due to the fact
# that one of the installed packages alters the available repo list and
# thus changes the list of packages available for yum to install.
RUN yum install -y openssl-devel-1.1.1k openssl-libs-1.1.1k

WORKDIR /

RUN rm -rf /tmp/grrdocker-scratch

CMD ["/bin/bash"]
