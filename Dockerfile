# A Docker image capable of running all GRR components.
#
# See https://hub.docker.com/r/grrdocker/grr/
#
# We have configured Github Actions to trigger an image build every time a new
# a PUSH happens in the GRR github repository.
#
# Example: Run the grr admin_ui component:
#
# docker run -it \
#   -v $(pwd)/docker_config_files:/configs
#   ghcr.io/google/grr:grr-docker-compose
#   "-component" "admin_ui"
#   "-config" "/configs/server/grr.server.yaml"

FROM ubuntu:22.04 AS builder

LABEL maintainer="grr-dev@googlegroups.com"

ENV DEBIAN_FRONTEND noninteractive
# Buffering output (sometimes indefinitely if a thread is stuck in
# a loop) makes for a non-optimal user experience when containers
# are run in the foreground, so we disable that.
ENV PYTHONUNBUFFERED 0

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

RUN pwd
RUN ls -lha
RUN ls -lha /

# Only available when building as part of Github Actions.
COPY ./_artifacts* /client_templates

ENV VIRTUAL_ENV /usr/share/grr-server
ENV GRR_SOURCE /usr/src/grr

RUN python -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN ${VIRTUAL_ENV}/bin/python -m pip install wheel nodeenv grpcio-tools==1.60

RUN nodeenv -p --prebuilt --node=16.13.0

RUN mkdir ${GRR_SOURCE}
ADD . ${GRR_SOURCE}

WORKDIR ${GRR_SOURCE}

RUN pip install -e grr/proto \
  pip install -e grr/core \
  pip install -e grr/client \
  pip install -e grr/server \
  pip install -e grr/client_builder \
  pip install -e api_client/python

RUN ${VIRTUAL_ENV}/bin/python grr/proto/makefile.py && \
  ${VIRTUAL_ENV}/bin/python grr/core/grr_response_core/artifacts/makefile.py

WORKDIR /

ENTRYPOINT [ "grr_server" ]