# A Docker container capable of running all GRR components.
FROM ubuntu:latest
MAINTAINER Greg Castle github@mailgreg.com

RUN mkdir -p /usr/share/grr/scripts
COPY scripts/install_script_ubuntu.sh /usr/share/grr/scripts/install_script_ubuntu.sh
COPY requirements.txt /usr/share/grr/requirements.txt
ENV UPGRADE=false
# Install our dependencies, use latest requirements.txt
RUN bash /usr/share/grr/scripts/install_script_ubuntu.sh -dy -r /usr/share/grr/requirements.txt

# Download the client templates now to get better caching from Docker.
WORKDIR /usr/share/grr
COPY scripts/download_client_templates.sh /usr/share/grr/scripts/download_client_templates.sh
RUN bash /usr/share/grr/scripts/download_client_templates.sh

# Copy the GRR code over
ADD . /usr/share/grr/

# Compile protos
RUN python makefile.py

# Install GRR
WORKDIR /usr/share/grr
RUN bash scripts/install_server_from_src.sh -d

COPY scripts/docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Server config, logs, sqlite db
VOLUME ["/etc/grr", "/var/log", "/var/grr-datastore"]

CMD ["grr"]
