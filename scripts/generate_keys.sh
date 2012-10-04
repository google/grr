#!/bin/bash
#
# Script to generate keys for the server and client signing components of GRR.
#
# By default this will generate keys in /etc/grr/keys
# To override set the KEYDIR environment variable.
#

# Allow KEYDIR to be overridden by environment variable.
if [ -z "${KEYDIR}" ];
then
  KEYDIR="/etc/grr/keys";
fi

# Set this to "OUT=&1" for debugging.
OUT="/dev/null"

if [ -e $KEYDIR/ca.pem ]; then
  echo "Found a ca certificate, looking for keys."
  if [ ! -e $KEYDIR/ca-key-priv.pem -o \
    ! -e $KEYDIR/ca-priv.pem -o \
    ! -e $KEYDIR/driver_sign.pem -o \
    ! -e $KEYDIR/driver_sign_pub.pem -o \
    ! -e $KEYDIR/exe_sign.pem -o \
    ! -e $KEYDIR/exe_sign_pub.pem -o \
    ! -e $KEYDIR/server.pem -o \
    ! -e $KEYDIR/server-priv.pem ]; then
    echo "Not all necessary key files found. Please clean directory to create new keys."
    exit
  fi;
  echo "Found all key files in $KEYDIR."
else

  echo "Generating keys"

  if [ "$(id -u)" != "0" ]; then
    echo "In order to write keys to $KEYDIR this script has to be run as root." 1>&2
    exit 1
  fi

  mkdir -p -m0755 $KEYDIR

  echo "Generating passphrase"
  PASSPHRASE=`openssl rand -base64 9`

  echo "Generating CA"
  openssl req -new -x509 -days 3650 -extensions v3_ca \
    -keyout $KEYDIR/ca-key-priv.pem -out $KEYDIR/ca.pem \
    -config /etc/ssl/openssl.cnf -batch -passout pass:$PASSPHRASE 2>$OUT

  echo 1000 > $KEYDIR/serial

  touch $KEYDIR/index.txt

  cat > $KEYDIR/ca.conf <<EOF
[ ca ]
default_ca      = CA_default             # The default ca section

[ CA_default ]
dir            = $KEYDIR                 # top dir
database       = $KEYDIR/index.txt       # index file.
new_certs_dir  = $KEYDIR                 # new certs dir

certificate    = $KEYDIR/ca.pem          # The CA cert
serial         = $KEYDIR/serial          # serial no file
private_key    = $KEYDIR/ca-key-priv.pem # CA private key
RANDFILE       = $KEYDIR/.rand           # random number file

default_days   = 365                     # how long to certify for
default_crl_days= 30                     # how long before next CRL
default_md     = md5                     # md to use
policy         = policy_any              # default policy
email_in_dn    = no                      # Don't add the email into cert DN
name_opt       = ca_default              # Subject name display option
cert_opt       = ca_default              # Certificate display option
copy_extensions = none                   # Don't copy extensions from request

[ policy_any ]
countryName            = optional
stateOrProvinceName    = optional
organizationName       = optional
organizationalUnitName = optional
commonName             = supplied
emailAddress           = optional

EOF


  echo "Generating server key"
  openssl req -new -nodes \
    -out $KEYDIR/server-req.pem \
    -keyout $KEYDIR/server-priv.pem \
    -config /etc/ssl/openssl.cnf -batch 2>$OUT

  echo "Generating server certificate"
  openssl ca \
    -config $KEYDIR/ca.conf \
    -out $KEYDIR/server.pem \
    -batch \
    -key $PASSPHRASE \
    -outdir $KEYDIR \
    -subj /CN=GRR \
    -infiles $KEYDIR/server-req.pem 2>$OUT

  echo "Exporting CA key"
  openssl rsa \
    -in $KEYDIR/ca-key-priv.pem \
    -out $KEYDIR/ca-priv.pem \
    -passin pass:$PASSPHRASE

  cat $KEYDIR/ca.pem >> $KEYDIR/ca-priv.pem
  cat $KEYDIR/server.pem >>$KEYDIR/server-priv.pem

  echo "Generating driver signing key"
  openssl genrsa -out $KEYDIR/driver_sign.pem 2048 2>$OUT
  openssl rsa -pubout -in $KEYDIR/driver_sign.pem -out $KEYDIR/driver_sign_pub.pem >$OUT

  echo "Generating executable code signing key"
  openssl genrsa -out $KEYDIR/exe_sign.pem 2048 2>$OUT
  openssl rsa -pubout -in $KEYDIR/exe_sign.pem -out $KEYDIR/exe_sign_pub.pem >$OUT

  echo "All done, cleaning up"
  rm $KEYDIR/1000.pem $KEYDIR/server-req.pem $KEYDIR/ca.conf $KEYDIR/serial* $KEYDIR/index.txt*

  echo "The generated keys are in $KEYDIR"

fi;
