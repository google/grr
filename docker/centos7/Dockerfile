# Docker file that builds a Centos 7 image with a recent version of
# Python installed.

FROM centos:7

LABEL maintainer="grr-dev@googlegroups.com"

WORKDIR /tmp/grrdocker-scratch

# Install pre-requisites for building Python, as well as GRR prerequisites.
RUN yum update -y && yum install -y make zlib-devel bzip2-devel ncurses-devel \
  sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel \
  xz-devel epel-release python-devel wget which java-1.8.0-openjdk \
  libffi-devel openssl-devel zip git gcc gcc-c++ redhat-rpm-config rpm-build \
  rpm-sign

# Install openssl11 for cryptography.
# Note: including openssl11-devel and openssl11-libs into the command above
# doesn't work (yum reports them as not found). This is likely due to the fact
# that one of the installed packages alters the available repo list and
# thus changes the list of packages available for yum to install.
RUN yum install -y openssl11-devel openssl11-libs

# Install devtools (without the manpages, see the --setopt=tsflags=nodocs flag)
# to ensure we have a fresh enough GCC version and Python extensions
# can be successfully compiled.
RUN yum install -y centos-release-scl-rh && \
    INSTALL_PKGS="devtoolset-7-gcc devtoolset-7-gcc-c++ devtoolset-7-gcc-gfortran devtoolset-7-gdb make" && \
    yum install -y --setopt=tsflags=nodocs $INSTALL_PKGS && \
    rpm -V $INSTALL_PKGS && \
    yum -y clean all --enablerepo='*'
RUN echo "source /opt/rh/devtoolset-7/enable" >> /etc/bashrc
SHELL ["/bin/bash", "--login", "-c"]
RUN gcc --version

WORKDIR /

RUN rm -rf /tmp/grrdocker-scratch

CMD ["/bin/bash"]
