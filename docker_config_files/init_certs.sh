#!/bin/bash
#
# Script to generate a set of keys and certificates for GRR and Fleetspeak that
# replace the placeholders in the config files.
#
# Usage:
# ./init_certs.sh

set -ex

FILE_DIR="$(dirname "$(which "$0")")"

# Generate key pair .pem files, which is linked in the GRR client and
# server configs (client.yaml, server.local.yaml).
openssl genrsa -out "$FILE_DIR/private-key.pem"
openssl rsa -in "$FILE_DIR/private-key.pem" -pubout -out "$FILE_DIR/public-key.pem"

# Create a CA/trusted private key and cert for Fleetspeak.
openssl genrsa \
    -out "$FILE_DIR/fleetspeak-ca-key.pem"
openssl req -new -x509 -days 365 -subj "/CN=Fleetspeak CA"\
   -key "$FILE_DIR/fleetspeak-ca-key.pem" \
   -out "$FILE_DIR/fleetspeak-ca-cert.pem" \

# Create keys for CA signed key and cert for fleetspeak. Resulting files are
# also copied in the envoy container, see containers/envoy/Dockerfile).
openssl genrsa \
    -out "$FILE_DIR/fleetspeak-key.pem"
openssl req -new -x509 -days 365 \
   -subj "/CN=Fleetspeak CA" -addext "subjectAltName = DNS:fleetspeak-frontend" \
   -key "$FILE_DIR/fleetspeak-key.pem" \
   -out "$FILE_DIR/fleetspeak-cert.pem" \
   -CA "$FILE_DIR/fleetspeak-ca-cert.pem" \
   -CAkey "$FILE_DIR/fleetspeak-ca-key.pem"

# Replace placeholders in fleetspeak and grr-client config files.
TRUSTED_FLEETSPEAK_CERT=$(sed ':a;N;$!ba;s/\n/\\\\n/g' "$FILE_DIR/fleetspeak-ca-cert.pem")
FLEETSPEAK_KEY=$(sed ':a;N;$!ba;s/\n/\\\\n/g' "$FILE_DIR/fleetspeak-key.pem")
FLEETSPEAK_CERT=$(sed ':a;N;$!ba;s/\n/\\\\n/g' "$FILE_DIR/fleetspeak-cert.pem")

sed -i 's@%FLEETSPEAK_CERT%@'"$FLEETSPEAK_CERT"'@' "$FILE_DIR/server/textservices/frontend.components.config"
sed -i 's@%FLEETSPEAK_KEY%@'"$FLEETSPEAK_KEY"'@' "$FILE_DIR/server/textservices/frontend.components.config"
sed -i 's@%TRUSTED_FLEETSPEAK_CERT%@'"$TRUSTED_FLEETSPEAK_CERT"'@' "$FILE_DIR/client/client.config"
