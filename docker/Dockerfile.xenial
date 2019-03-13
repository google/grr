# Docker file that builds an Ubuntu Xenial image ready for GRR installation.
#
# To build a new image on your local machine, cd to this file's directory
# and run (note the period at the end):
#
#   docker build -t grrdocker/xenial -f Dockerfile.xenial .

FROM ubuntu:xenial

LABEL maintainer="grr-dev@googlegroups.com"

WORKDIR /tmp/grrdocker-scratch

RUN apt update -qq && \
  apt install -y locales fakeroot debhelper libffi-dev git attr \
  libssl-dev python-dev python-pip wget openjdk-8-jdk zip devscripts \
  dh-systemd libmysqlclient-dev dh-virtualenv dh-make libc6-i386 lib32z1

# Dependencies and environment variables required to build CHIPSEC from source.
ENV LINUX_HEADERS_VERSION="4.15.0-46-generic"
RUN apt update -qq && apt install -y \
  build-essential gcc nasm linux-headers-${LINUX_HEADERS_VERSION}
ENV KERNEL_SRC_DIR="/lib/modules/${LINUX_HEADERS_VERSION}/build"

# Install pip, virtualenv, chrome and set up locales.
RUN pip install --upgrade pip virtualenv && \
  wget --quiet https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
  apt install -y ./google-chrome-stable_current_amd64.deb && \
  sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
  locale-gen && \
  update-locale LANG="en_US.UTF-8" LANGUAGE="en_US:en" LC_ALL="en_US.UTF-8"

# Add chrome to PATH and set locale-related environment variables.
ENV PATH="${PATH}:/opt/google/chrome" LANG="en_US.UTF-8" LANGUAGE="en_US:en" LC_ALL="en_US.UTF-8"

WORKDIR /

RUN rm -rf /tmp/grrdocker-scratch

CMD ["/bin/bash"]
