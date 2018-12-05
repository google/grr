#!/usr/bin/env python
"""This file contains utility classes related to maintenance used by GRR."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import sys



from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import key_utils
from grr_response_server import signed_binary_utils

SUPPORTED_PLATFORMS = ["windows", "linux", "darwin"]
SUPPORTED_ARCHITECTURES = ["i386", "amd64"]


def EPrint(message):
  sys.stderr.write("%s\n" % message)


def UploadSignedConfigBlob(content,
                           aff4_path,
                           client_context=None,
                           limit=None,
                           token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: File content to upload.
    aff4_path: aff4 path to upload to.
    client_context: The configuration contexts to use.
    limit: The maximum size of the chunk to use.
    token: A security token.

  Raises:
    IOError: On failure to write.
  """
  if limit is None:
    limit = config.CONFIG["Datastore.maximum_blob_size"]

  # Get the values of these parameters which apply to the client running on the
  # target platform.
  if client_context is None:
    # Default to the windows client.
    client_context = ["Platform:Windows", "Client Context"]

  config.CONFIG.Validate(
      parameters="PrivateKeys.executable_signing_private_key")

  signing_key = config.CONFIG.Get(
      "PrivateKeys.executable_signing_private_key", context=client_context)

  verification_key = config.CONFIG.Get(
      "Client.executable_signing_public_key", context=client_context)

  signed_binary_utils.WriteSignedBinary(
      rdfvalue.RDFURN(aff4_path),
      content,
      signing_key,
      public_key=verification_key,
      chunk_size=limit,
      token=token)

  logging.info("Uploaded to %s", aff4_path)


def RotateServerKey(cn=u"grr", keylength=4096):
  """This function creates and installs a new server key.

  Note that

  - Clients might experience intermittent connection problems after
    the server keys rotated.

  - It's not possible to go back to an earlier key. Clients that see a
    new certificate will remember the cert's serial number and refuse
    to accept any certificate with a smaller serial number from that
    point on.

  Args:
    cn: The common name for the server to use.
    keylength: Length in bits for the new server key.
  Raises:
    ValueError: There is no CA cert in the config. Probably the server
                still needs to be initialized.
  """
  ca_certificate = config.CONFIG["CA.certificate"]
  ca_private_key = config.CONFIG["PrivateKeys.ca_key"]

  if not ca_certificate or not ca_private_key:
    raise ValueError("No existing CA certificate found.")

  # Check the current certificate serial number
  existing_cert = config.CONFIG["Frontend.certificate"]

  serial_number = existing_cert.GetSerialNumber() + 1
  EPrint("Generating new server key (%d bits, cn '%s', serial # %d)" %
         (keylength, cn, serial_number))

  server_private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=keylength)
  server_cert = key_utils.MakeCASignedCert(
      unicode(cn),
      server_private_key,
      ca_certificate,
      ca_private_key,
      serial_number=serial_number)

  EPrint("Updating configuration.")
  config.CONFIG.Set("Frontend.certificate", server_cert.AsPEM())
  config.CONFIG.Set("PrivateKeys.server_key", server_private_key.AsPEM())
  config.CONFIG.Write()

  EPrint("Server key rotated, please restart the GRR Frontends.")
