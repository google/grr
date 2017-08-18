# A Docker container capable of running all GRR components.
FROM ubuntu:xenial

LABEL maintainer="grr-dev@googlegroups.com"

SHELL ["/bin/bash", "-c"]

ENV GRR_VENV /usr/share/grr-server
ENV PROTOC /usr/share/protobuf/bin/protoc

RUN apt-get update && \
  apt-get install -y \
  debhelper \
  default-jre \
  dpkg-dev \
  git \
  libffi-dev \
  libssl-dev \
  python-dev \
  python-pip \
  rpm \
  wget \
  zip

RUN pip install --upgrade pip virtualenv

# Install proto compiler
RUN mkdir -p /usr/share/protobuf && \
cd /usr/share/protobuf && \
wget --quiet "https://github.com/google/protobuf/releases/download/v3.3.0/protoc-3.3.0-linux-x86_64.zip" && \
unzip protoc-3.3.0-linux-x86_64.zip

# Make sure Bower will be able to run as root.
# Install nodeenv, a prebuilt version of NodeJS and update the virtualenv
# environment.
# Pull dependencies and templates from pypi and build wheels so docker can cache
# them. This just makes the actual install go faster.
RUN echo '{ "allow_root": true }' > /root/.bowerrc

RUN virtualenv $GRR_VENV

RUN $GRR_VENV/bin/pip install --upgrade wheel six setuptools nodeenv

# TODO(ogaro) Stop hard-coding the node version to install
# when a Linux node-sass binary compatible with node v8.0.0 is
# available: https://github.com/sass/node-sass/pull/1969
RUN $GRR_VENV/bin/nodeenv -p --prebuilt --node=7.10.0

# Copy the GRR code over.
ADD . /usr/src/grr

WORKDIR /usr/src/grr

RUN source $GRR_VENV/bin/activate && python setup.py sdist --formats=zip --dist-dir=/sdists --no-make-docs

RUN $GRR_VENV/bin/python grr/config/grr-response-client/setup.py sdist --formats=zip --dist-dir=/sdists

RUN $GRR_VENV/bin/python api_client/python/setup.py sdist --formats=zip --dist-dir=/sdists

RUN $GRR_VENV/bin/python grr/config/grr-response-server/setup.py sdist --formats=zip --dist-dir=/sdists

RUN $GRR_VENV/bin/pip install --find-links=/sdists /sdists/grr-response-server-*.zip

WORKDIR /

COPY scripts/docker-entrypoint.sh .

ENTRYPOINT ["/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Server config, logs, sqlite db
VOLUME ["/etc/grr", "/var/log", "/var/grr-datastore"]

CMD ["grr"]
