# This is a single monolithic container that runs all the GRR services. It is
# only intended for running a demo server since it ignores most of the benefits
# of horizontal scaling with Docker. Per-component dockerfiles are coming soon.
FROM ubuntu:latest
MAINTAINER Greg Castle github@mailgreg.com

RUN mkdir -p /usr/share/grr/scripts
COPY scripts/install_script_ubuntu.sh /usr/share/grr/scripts/install_script_ubuntu.sh
ENV UPGRADE=false
RUN bash /usr/share/grr/scripts/install_script_ubuntu.sh -dy

COPY grr-server_0.3.0-7_amd64.deb grr-server_0.3.0-7_amd64.deb
RUN dpkg -i grr-server_0.3.0-7_amd64.deb

WORKDIR /
COPY travis/requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Get current rekall - uncomment when it installs cleanly
#RUN apt-get -y update && apt-get install -y git
#RUN git clone https://github.com/google/rekall.git
#WORKDIR rekall
#RUN python setup.py install

# Copy the GRR code over
ADD . /usr/share/grr/

# Compile protos
WORKDIR /usr/share/grr/proto
RUN make

WORKDIR /usr/share/grr

# Remove old grr installed by the deb package, we're going to overwrite it with
# the repository version.
RUN rm -rf /usr/lib/python2.7/dist-packages/grr
RUN python setup.py build && python setup.py install

COPY scripts/docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

# Port for the admin UI GUI
EXPOSE 8000

# Port for clients to talk to
EXPOSE 8080

# Server config, logs, sqlite db
VOLUME ["/etc/grr", "/var/log", "/var/grr-datastore"]

CMD ["grr"]
