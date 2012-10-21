#!/bin/sh
#
# Post installation script for GRR client MacOS-X package

LAUNCHCTL_PLIST="/Library/LaunchDaemons/com.google.code.grrd.plist";

if [ -f ${LAUNCHCTL_PLIST} ];
then
  sudo launchctl load ${LAUNCHCTL_PLIST};
fi

OLD_PLIST="/System/Library/LaunchDaemons/com.google.code.grrd.plist";

# Clean up some old versions.
if [ -f ${OLD_PLIST} ];
then
  sudo launchctl unload ${OLD_PLIST}
  sudo rm ${OLD_PLIST}
  true
fi
