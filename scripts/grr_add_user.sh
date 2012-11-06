#!/bin/bash
#
# Script to add a user.
#
#

PREFIX=/usr
HTACCESS=/etc/grr/grr-ui.htaccess
CONSOLE=${PREFIX}/bin/grr_console.py

read -p "Enter user name to add: " USERNAME;
if [ -f ${HTACCESS} ]; then
  sudo htpasswd -d ${HTACCESS} ${USERNAME};
else
  sudo htpasswd -c -d ${HTACCESS} ${USERNAME};
fi
if [ $? -ne 0 ]; then
  echo "ERROR: could not set password!"
  exit 1
fi

# Call the console to make user admin.
read -p "Make user ${USERNAME} an admin? (extra functionality in the Web interface) [Yn]: " REPLY;
case $REPLY in
  y|Y)  if [ ! -x ${CONSOLE} ]; then
          echo "Cannot run as $CONSOLE is not available.";
          exit 1;
        fi
        echo "MakeUserAdmin('${USERNAME}', user_must_exist=False)" | ${CONSOLE} > /dev/null
        ;;
esac

