#!/bin/sh
#
# MacOS pre-installation script for GRR [Fleetspeak-enabled].

[[ "${3}" != '/' ]] && exit 0

# Non-Fleetspeak clients install a plist file; Use it to stop the client
# processes if it exists.
if [[ -f '%(Client.plist_path)' ]]; then
  sudo launchctl unload '%(Client.plist_path)'
  sudo rm -f '%(Client.plist_path)'
fi

# Note that non-Fleetspeak clients install GRR to
# /usr/local/lib/<Client.name>/<Client.name>_<Source.version_string>_<Client.arch>
# by default. Fleetspeak-enabled clients on the other hand, by
# default do not have the version in the install path.
if [[ -e '%(ClientBuilder.install_dir)' ]]; then
  tmpdir=`mktemp -d -t '%(Client.name)_%(Source.version_string)_install'`
  sudo mv '%(ClientBuilder.install_dir)' "${tmpdir}"
fi
