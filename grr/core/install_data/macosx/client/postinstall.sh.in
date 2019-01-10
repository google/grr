#!/bin/sh
#
# Post installation script for GRR client MacOS-X package

[[ $3 != "/" ]] && exit -1

# Run the installation routines.
"%(ClientBuilder.install_dir)/%(Client.binary_name)" --install --config="%(ClientBuilder.install_dir)/%(ClientBuilder.config_filename)"

if [ $? -ne 0 ]
then
  exit -1
fi

if [ -f "%(Client.plist_path)" ];
then
  sudo launchctl load -w "%(Client.plist_path)";
fi

exit 0
