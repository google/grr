#!/bin/bash

# The main entry point to all GRR tools for debian installations. This simple
# script sources the main debian configuration file at /etc/default/grr and
# appends all its parameters to the specific grr tools used.

# The main use case is to provide a single point where users may switch GRR
# installations. For example a common use case is to install an updated GRR
# installation from source:
# http://grr-doc.readthedocs.io/en/stable/installing-grr-server/from-released-pip.html

# While this could be handled by systemd drop-in overrides for the services, we
# would need to do something for the other components (grr_config_updater,
# grr_console etc.). So we wrap grr_server (which is itself a wrapper), so that
# we can have a single configuration point for everything.

GLOBAL_DEFAULT_FILE="/etc/default/grr-server"

# Load the global default file for the location of the GRR virtual env.
. ${GLOBAL_DEFAULT_FILE}

# NAME will be: grr_server, grr_config_updater, grr_console
# grr_fuse, or similar.
NAME=$(basename "$0")

if ! [ -x "${GRR_PREFIX}" ] ; then
  echo "Can not find GRR's virtual env location. Please adjust the GRR_PREFIX location in ${GLOBAL_DEFAULT_FILE}."
  exit 1
fi

# Run the script.
# $@ is expanded specially and should be quoted:
# http://www.gnu.org/software/bash/manual/bash.html#Special-Parameters
"${GRR_PREFIX}/bin/${NAME}" "${@}"
