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

FROM mariadb:bionic

LABEL maintainer="grr-dev@googlegroups.com"

ARG GCS_BUCKET
ARG GRR_COMMIT

ENV GRR_VENV /usr/share/grr-server
ENV DEBIAN_FRONTEND noninteractive
# Buffering output (sometimes indefinitely if a thread is stuck in
# a loop) makes for a non-optimal user experience when containers
# are run in the foreground, so we disable that.
ENV PYTHONUNBUFFERED=0

SHELL ["/bin/bash", "-c"]

RUN apt-get update && \
  apt-get install -y \
  debhelper \
  default-jre \
  dpkg-dev \
  git \
  libffi-dev \
  libssl-dev \
  python3-dev \
  python3-pip \
  python3-venv \
  rpm \
  wget \
  zip \
  python3-mysqldb

RUN pip3 install --upgrade setuptools && \
    python3 -m venv --system-site-packages $GRR_VENV

RUN $GRR_VENV/bin/pip install --upgrade --no-cache-dir pip wheel six setuptools nodeenv && \
    $GRR_VENV/bin/nodeenv -p --prebuilt --node=16.13.0 && \
    echo '{ "allow_root": true }' > /root/.bowerrc

# Copy the GRR code over.
ADD . /usr/src/grr

RUN cd /usr/src/grr && bash -x /usr/src/grr/docker/install_grr_from_gcs.sh

ENTRYPOINT ["/usr/src/grr/docker/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Directories used by GRR at runtime, which can be mounted from the host's
# filesystem. Note that volumes can be mounted even if they do not appear in
# this list.
VOLUME ["/usr/share/grr-server/install_data/etc"]

CMD ["grr"]
