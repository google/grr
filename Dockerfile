# A Docker container capable of running all GRR components.
FROM ubuntu:xenial
MAINTAINER Greg Castle github@mailgreg.com

RUN apt-get update && \
  apt-get install -y \
  debhelper \
  default-jre \
  dpkg-dev \
  git \
  libffi-dev \
  libssl-dev \
  prelink \
  python-dev \
  python-pip \
  rpm \
  wget \
  zip && \
  pip install --upgrade pip && \
  pip install virtualenv && \
  pip install setuptools --upgrade && \
  virtualenv /usr/share/grr-server

# Install proto compiler
RUN mkdir -p /usr/share/protobuf && \
cd /usr/share/protobuf && \
wget --quiet "https://github.com/google/protobuf/releases/download/v3.2.0/protoc-3.2.0-linux-x86_64.zip" && \
unzip protoc-3.2.0-linux-x86_64.zip
ENV PROTOC /usr/share/protobuf/bin/protoc

# Make sure Bower will be able to run as root.
# Install nodeenv, a prebuilt version of NodeJS and update the virtualenv
# environment.
# Pull dependencies and templates from pypi and build wheels so docker can cache
# them. This just makes the actual install go faster.
RUN echo '{ "allow_root": true }' > /root/.bowerrc && \
. /usr/share/grr-server/bin/activate && \
pip install nodeenv && \
nodeenv -p --prebuilt && \
. /usr/share/grr-server/bin/activate && \
mkdir /wheelhouse && \
pip wheel --wheel-dir=/wheelhouse --pre grr-response-server && \
pip wheel --wheel-dir=/wheelhouse -f https://storage.googleapis.com/releases.grr-response.com/index.html grr-response-templates

# Copy the GRR code over.
ADD . /usr/src/grr/

# Make sdists and pip install
# We require sdists so that the version.ini gets copied over properly.
RUN . /usr/share/grr-server/bin/activate && \
cd /usr/src/grr/ && \
python /usr/src/grr/setup.py sdist --dist-dir="/sdists/core" --no-make-docs && \
cd /usr/src/grr/grr/config/grr-response-server/ && \
python setup.py sdist --dist-dir="/sdists/server" && \
pip install --find-links=/wheelhouse /sdists/core/*.tar.gz && \
pip install --find-links=/wheelhouse /sdists/server/*.tar.gz && \
pip install --find-links=/wheelhouse grr_response_templates

COPY scripts/docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Server config, logs, sqlite db
VOLUME ["/etc/grr", "/var/log", "/var/grr-datastore"]

CMD ["grr"]
