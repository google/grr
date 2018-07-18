# A Docker image capable of running all GRR components.
#
# See https://hub.docker.com/r/grrdocker/grr/
#
# We have configured Travis to trigger an image build every time a new server
# deb is been uploaded to GCS.
#
# Run the container with:
#
# docker run \
#    -e EXTERNAL_HOSTNAME="localhost" \
#    -e ADMIN_PASSWORD="demo" \
#    -p 0.0.0.0:8000:8000 \
#    -p 0.0.0.0:8080:8080 \
#    grrdocker/grr

FROM ubuntu:xenial

LABEL maintainer="grr-dev@googlegroups.com"

ENV GRR_VENV /usr/share/grr-server
ENV PROTOC /usr/share/protobuf/bin/protoc

SHELL ["/bin/bash", "-c"]

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

RUN pip install --upgrade --no-cache-dir pip virtualenv && virtualenv $GRR_VENV

# Install proto compiler
RUN mkdir -p /usr/share/protobuf && \
cd /usr/share/protobuf && \
wget --quiet "https://github.com/google/protobuf/releases/download/v3.3.0/protoc-3.3.0-linux-x86_64.zip" && \
unzip protoc-3.3.0-linux-x86_64.zip && \
rm protoc-3.3.0-linux-x86_64.zip

# TODO(ogaro) Stop hard-coding the node version to install
# when a Linux node-sass binary compatible with node v8.0.0 is
# available: https://github.com/sass/node-sass/pull/1969
RUN $GRR_VENV/bin/pip install --upgrade --no-cache-dir wheel six setuptools nodeenv && \
    $GRR_VENV/bin/nodeenv -p --prebuilt --node=7.10.0 && \
    echo '{ "allow_root": true }' > /root/.bowerrc

# Copy the GRR code over.
ADD . /usr/src/grr

RUN cd /usr/src/grr && /usr/src/grr/docker/install_grr_from_gcs.sh

ENTRYPOINT ["/usr/src/grr/grr/core/scripts/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Directories used by GRR at runtime, which can be mounted from the host's
# filesystem. Note that volumes can be mounted even if they do not appear in
# this list.
VOLUME ["/usr/share/grr-server/install_data/etc", "/usr/share/grr-server/lib/python2.7/site-packages/grr/var/grr-datastore"]

CMD ["grr"]
