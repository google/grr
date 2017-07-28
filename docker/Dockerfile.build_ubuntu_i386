FROM ubuntu_i386:xenial_base

LABEL maintainer="grr-dev@googlegroups.com"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update

# Install python
RUN apt-get install -y python3 && apt-get install -y python

# Install other required packages
RUN apt-get install -y zip \
  wget \
  openjdk-8-jdk \
  python-pip \
  git \
  debhelper \
  libffi-dev \
  libssl-dev \
  python-dev

RUN pip install --upgrade pip virtualenv

CMD ["/bin/bash"]
