#!/usr/bin/env python
"""A console script to create new server keys.

Use this script to make a new server key and certificate. You can just run the
script inside a console using `run -i make_new_server_key.py`.
"""
from grr import config
from grr.lib.rdfvalues import crypto
from grr.server import key_utils

ca_certificate = config.CONFIG["CA.certificate"]
ca_private_key = config.CONFIG["PrivateKeys.ca_key"]

# Check the current certificate serial number
existing_cert = config.CONFIG["Frontend.certificate"]
print "Current serial number:", existing_cert.GetSerialNumber()

server_private_key = crypto.RSAPrivateKey.GenerateKey(bits=4096)
server_cert = key_utils.MakeCASignedCert(
    u"grr",
    server_private_key,
    ca_certificate,
    ca_private_key,
    serial_number=existing_cert.GetSerialNumber() + 1)

print "New Server cert (Frontend.certificate):"
print server_cert.AsPEM()

print "New Server Private Key:"
print server_private_key.AsPEM()
