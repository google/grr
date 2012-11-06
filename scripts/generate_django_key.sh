#!/bin/bash
#
# Simple script to generate the CSRF/XSRF secret key and put it in the right
# place.
#
# By default this will generate a key and put it in /etc/grr/grr-server.conf.
# To override set the CONF_FILE environment variable.
#

if [ -z "${CONF_FILE}" ];
then
  CONF_FILE="/etc/grr/grr-server.conf"
fi


if [ -f ${CONF_FILE} ];
then
  echo "Generating django secret key."
  echo "";
  SECRET_KEY=`dd if=/dev/urandom count=10 2>/dev/null| strings | tr -dc "[:alnum:]"`;
  sed -i "s/CHANGE_ME/${SECRET_KEY}/" ${CONF_FILE};
else
  echo "WARNING: unable to generate django secret key ${CONF_FILE} does not exist".
  echo "Replace CHANGE_ME in: ${CONF_FILE}";
  echo "";
fi
