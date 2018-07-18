#!/bin/sh
#
# Pre installation script for GRR client MacOS-X package

[[ $3 != "/" ]] && exit 0

if [ -f "%(Client.plist_path)" ];
then
  sudo launchctl unload "%(Client.plist_path)";
  sudo rm -f "%(Client.plist_path)";
fi

