# A Docker image capable of running all GRR components.
#
# See https://github.com/google/grr/pkgs/container/grr
#
# We have configured Github Actions to trigger an image build every
# time a new a PUSH happens in the GRR github repository.
#
# Examples:
# - Run a GRR server component (e.g. admin_ui):
#
#   $ docker run -it \
#       -v $(pwd)/docker_config_files/server:/configs \
#       ghcr.io/google/grr:latest \
#       "-component" "admin_ui" \
#       "-config" "/configs/grr.server.yaml"
#
# - Run the GRR client component via repacking client templates:
#   Client installers for different operating systems are created by
#   repacking client templates, which are included in the GRR Docker image
#   downloaded from github (they are currently only build in the github workflow
#   that creates the GRR Docker image and not in a local build). The Fleetspeak
#   client requires connectivity to the Fleetspeak server, we recommend running
#   this client in the Docker Compose stack (see compose.yaml for details)
#   otherwise the config needs to be adjusted. The Docker Compose stack is also
#   taking care of repacking the client templates and installing them in the
#   GRR client container.
#
#   If you nontheless want to repack the client templates, install them in
#   a local container and start the client, you can use the following commands:
#
#   -- Start the container and mount the client config directory:
#       $ docker run -it \
#          -v $(pwd)/docker_config_files/client:/configs \
#          --entrypoint /bin/bash \
#          ghcr.io/google/grr:latest
#
#   -- The previous command will leave you with an open shell in
#      the container. Repack the client template and install the
#      resulting debian file inside the container:
#       root@<CONTAINER ID> $ /configs/repack_install_client.sh
#
#   -- Start Fleetspeak and GRR clients:
#       root@<CONTAINER ID> $ fleetspeak-client -config /configs/client.config
#
#   -- (Optional) To verify if the client runs, check if the two expected
#      processes are running:
#       root@<CONTAINER ID> $ ps aux
#             ...        COMMAND
#             ...        fleetspeak-client -config /configs/client.config
#             ...        python -m grr_response_client.client ...
# - To run a GRR client container without repacking checkout out the
#   Dockerfile.client file.

FROM ubuntu:22.04

LABEL maintainer="grr-dev@googlegroups.com"

ENV DEBIAN_FRONTEND=noninteractive
# Buffering output (sometimes indefinitely if a thread is stuck in
# a loop) makes for a non-optimal user experience when containers
# are run in the foreground, so we disable that.
ENV PYTHONUNBUFFERED=0

RUN apt-get update && \
  apt-get install -y \
  default-jre \
  python-is-python3 \
  python3-dev \
  python3-pip \
  python3-venv \
  python3-mysqldb \
  build-essential \
  linux-headers-generic \
  dh-make \
  rpm

# Copy the client installers to the image, only available when
# building as part of Github Actions.
COPY ./_installers* /client_templates

ENV VIRTUAL_ENV=/usr/share/grr-server
ENV GRR_SOURCE=/usr/src/grr

RUN python -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH=${VIRTUAL_ENV}/bin:${PATH}

RUN ${VIRTUAL_ENV}/bin/python -m pip install wheel nodeenv grpcio-tools==1.60

RUN ${VIRTUAL_ENV}/bin/nodeenv -p --prebuilt --node=22.14.0

RUN mkdir -p ${GRR_SOURCE}
ADD . ${GRR_SOURCE}

WORKDIR ${GRR_SOURCE}

RUN ${VIRTUAL_ENV}/bin/python -m pip install \
  -e grr/proto \
  -e grr/core \
  -e grr/client \
  -e grr/server \
  -e grr/client_builder \
  -e api_client/python

RUN ${VIRTUAL_ENV}/bin/python grr/proto/makefile.py && \
  ${VIRTUAL_ENV}/bin/python grr/core/grr_response_core/artifacts/makefile.py

ENTRYPOINT [ "grr_server" ]
