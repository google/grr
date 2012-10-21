#!/bin/bash
#
# Script to install pmem memory drivers into GRR.
#
# By default this will use keys in /etc/grr/keys and install into /usr/share/grr
# Note that this will prompt you for passphrases if you have protected your
# signing keys.
#
#

OSX_PMEM_URL="https://volatility.googlecode.com/svn/branches/scudette/tools/osx/OSXPMem/OSXPMem-RC1.tar.gz"
WIN_PMEM_URL_BASE="https://volatility.googlecode.com/svn/branches/scudette/tools/windows/winpmem/binaries"

CONFIG_UPDATER="/usr/bin/grr_config_updater.py"

# Variable to store if the user has answered "Yes to All"
ALL_YES=0;


function header()
{
  echo ""
  echo "##########################################################################################"
  echo "     ${*}";
  echo "##########################################################################################"
}

function run_header() { echo "#### Running #### ${*}"; }

function exit_fail() {
  FAIL=$*;
  echo "#########################################################################################";
  echo "FAILURE RUNNING: ${FAIL}";
  echo "#########################################################################################";
  exit 0
};


function run_cmd_confirm()
{
  CMD=$*;
  echo ""
  if [ ${ALL_YES} = 0 ]; then
    read -p "Run ${CMD} [y/N/a]? " REPLY
    case $REPLY in
      y|Y) run_header ${CMD};;
      a|A) echo "Answering yes from now on"; ALL_YES=1;;
      *) return ;;
    esac
  fi
  ${CMD};
  RETVAL=$?
  if [ $RETVAL -ne 0 ]; then
    exit_fail $CMD;
  fi
};


header "Downloading winpmem drivers"
run_cmd_confirm wget ${WIN_PMEM_URL_BASE}/amd64/winpmem_64.sys;
run_cmd_confirm wget ${WIN_PMEM_URL_BASE}/i386/winpmem_32.sys;
run_cmd_confirm wget ${OSX_PMEM_URL};


header "Sign and upload OSX pmem driver"
OSX_PMEM=$(basename ${OSX_PMEM_URL});
UNPACKED=$(echo ${OSX_PMEM} | cut -d "." -f -2);

# Hack to remove unecessary files from gzip before we sign them.
# OSX wants tar.gz of directory with just kext dir in it.
run_cmd_confirm gunzip ${OSX_PMEM};
run_cmd_confirm tar --delete OSXPMem/osxpmem -f ${UNPACKED};
run_cmd_confirm tar --delete OSXPMem/README -f ${UNPACKED};
run_cmd_confirm gzip ${UNPACKED};
CMD="${CONFIG_UPDATER} --action=BOTH --file=${OSX_PMEM} --type=DRIVER --install_driver_name=pmem --install_device_path=/dev/pmem --install_rewrite_mode=FORCE --signing_key=/etc/grr/keys/driver_sign.pem --verification_key=/etc/grr/keys/driver_sign_pub.pem --platform=OSX --upload_name=pmem --aff4_path=/config/drivers/osx/memory";
run_cmd_confirm ${CMD};

header "Sign and upload Windows pmem drivers (32 & 64 bit)"
CMD="${CONFIG_UPDATER} --action=BOTH --file=winpmem_32.sys --type=DRIVER --install_driver_name=pmem --install_device_path=\\\\.\\pmem --install_rewrite_mode=FORCE --signing_key=/etc/grr/keys/driver_sign.pem --verification_key=/etc/grr/keys/driver_sign_pub.pem --platform=WINDOWS --upload_name=winpmem.32.sys --aff4_path=/config/drivers/windows/memory";
run_cmd_confirm ${CMD};

CMD="${CONFIG_UPDATER} --action=BOTH --file=winpmem_64.sys --type=DRIVER --install_driver_name=pmem --install_device_path=\\\\.\\pmem --install_rewrite_mode=FORCE --signing_key=/etc/grr/keys/driver_sign.pem --verification_key=/etc/grr/keys/driver_sign_pub.pem --platform=WINDOWS --upload_name=winpmem.64.sys --aff4_path=/config/drivers/windows/memory";
run_cmd_confirm ${CMD};


echo "############################################################################################"
echo "Driver install complete."
echo "If this worked you should now see them under Manage Binaries in the Admin UI."
echo "############################################################################################"
