# A Docker container capable of running all GRR components.
FROM ubuntu:latest
MAINTAINER Greg Castle github@mailgreg.com

RUN mkdir -p /usr/share/grr/scripts
COPY scripts/install_script_ubuntu.sh /usr/share/grr/scripts/install_script_ubuntu.sh
ENV UPGRADE=false
# Install our dependencies
RUN bash /usr/share/grr/scripts/install_script_ubuntu.sh -dy

# Download the client templates now to get better caching from Docker.
WORKDIR /usr/share/grr
COPY scripts/download_client_templates.sh /usr/share/grr/scripts/download_client_templates.sh
RUN bash /usr/share/grr/scripts/download_client_templates.sh

# Get current rekall
RUN apt-get -y update && apt-get install -y git && \
  git clone https://github.com/google/rekall.git && \
  cd rekall && \
  python setup.py sdist install

# Copy the GRR code over
ADD . /usr/share/grr/

# Compile protos
WORKDIR /usr/share/grr/proto
RUN make

# Install GRR
WORKDIR /usr/share/grr
ENV DOWNLOAD_CLIENT_TEMPLATES=false
ENV DOCKER=true
RUN bash scripts/install_server_from_src.sh

COPY scripts/docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Server config, logs, sqlite db
VOLUME ["/etc/grr", "/var/log", "/var/grr-datastore"]

CMD ["grr"]
