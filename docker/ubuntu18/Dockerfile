# Docker file that builds an Ubuntu Bionic image ready for GRR installation.

FROM ubuntu:bionic

LABEL maintainer="grr-dev@googlegroups.com"

WORKDIR /tmp/grrdocker-scratch

RUN apt update -qq && \
  apt install -y locales fakeroot debhelper libffi-dev git attr \
  libssl-dev python-dev python-pip wget openjdk-8-jdk zip devscripts \
  dh-systemd libmysqlclient-dev dh-virtualenv dh-make libc6-i386 lib32z1 \
  zlib1g-dev libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
  libbz2-dev libexpat1-dev liblzma-dev libffi-dev uuid-dev build-essential

# Dependencies and environment variables required to build CHIPSEC from source.
ENV LINUX_HEADERS_VERSION="4.15.0-46-generic"
RUN apt update -qq && apt install -y \
  gcc nasm linux-headers-${LINUX_HEADERS_VERSION}
ENV KERNEL_SRC_DIR="/lib/modules/${LINUX_HEADERS_VERSION}/build"

# Set locale-related environment variables.
ENV LANG="en_US.UTF-8" LANGUAGE="en_US:en" LC_ALL="en_US.UTF-8"

WORKDIR /

RUN rm -rf /tmp/grrdocker-scratch

CMD ["/bin/bash"]
