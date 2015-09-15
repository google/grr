# A Docker container capable of running all GRR components.
FROM ubuntu:latest
MAINTAINER Greg Castle github@mailgreg.com

RUN mkdir -p /usr/share/grr/scripts
COPY scripts/install_script_ubuntu.sh /usr/share/grr/scripts/install_script_ubuntu.sh
ENV UPGRADE=false
RUN bash /usr/share/grr/scripts/install_script_ubuntu.sh -dy

# Avoid storing a copy of the deb to keep image size down. We're using the deb
# to deliver client templates and set up init scripts and config directories.
# Actual python code will be overwritten with the latest from the repo in a
# later step.
RUN wget --quiet https://googledrive.com/host/0B1wsLqFoT7i2c3F0ZmI1RDJlUEU/test-grr-server_0.3.0-8_amd64.deb && \
  dpkg --install test-grr-server_0.3.0-8_amd64.deb && \
  rm -f test-grr-server_0.3.0-8_amd64.deb

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

WORKDIR /usr/share/grr
# Remove old grr installed by the deb package and overwrite it with
# the repository version.
RUN rm -rf /usr/lib/python2.7/dist-packages/grr && \
  python setup.py build && python setup.py install

COPY scripts/docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Server config, logs, sqlite db
VOLUME ["/etc/grr", "/var/log", "/var/grr-datastore"]

CMD ["grr"]
