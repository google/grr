#!/bin/sh
#
# MacOS post-installation script for GRR [Fleetspeak-enabled].

[[ "${3}" != '/' ]] && exit -1

# Use the config generated during client repacking as the
# primary config.
if [[ -f "${PACKAGE_PATH}" ]]; then
  unzip -p "${PACKAGE_PATH}" config.yaml > '%(ClientBuilder.install_dir)/%(ClientBuilder.config_filename)'
fi

# If client.config is present in the ZIP file, this is a bundled fleetspeak installation.
if unzip -l "${PACKAGE_PATH}" client.config > /dev/null 2>&1; then
  # Extract the fleetspeak client config.
  unzip -p "${PACKAGE_PATH}" client.config > /etc/fleetspeak-client/client.config
  fleetspeak_plist_path="/Library/LaunchDaemons/com.google.code.fleetspeak.plist"
else
  fleetspeak_plist_path="%(ClientBuilder.fleetspeak_plist_path)"
fi

# Restart Fleetspeak so it picks up GRR's service config.
if [[ -f "$fleetspeak_plist_path" ]]; then
  launchctl unload "$fleetspeak_plist_path"
  launchctl load "$fleetspeak_plist_path"
fi

exit 0
