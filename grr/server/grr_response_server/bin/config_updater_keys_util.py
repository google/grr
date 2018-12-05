#!/usr/bin/env python
"""Utilities for generting GRR keys as part of config_updater run."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from grr_response_core import config as grr_config
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import key_utils


class Error(Exception):
  """Base class for module-specific errors."""


class OpenSourceKeyUtilsRequiredError(Error):
  """Raised when OS key_utils implementation is not found."""


class KeysAlreadyExistError(Error):
  """Raised when keys we're about to generate are already present."""


def _GenerateCSRFKey(config):
  """Update a config with a random csrf key."""
  secret_key = config.Get("AdminUI.csrf_secret_key", None)
  if not secret_key:
    # TODO(amoser): Remove support for django_secret_key.
    secret_key = config.Get("AdminUI.django_secret_key", None)
    if secret_key:
      config.Set("AdminUI.csrf_secret_key", secret_key)

  if not secret_key:
    key = utils.GeneratePassphrase(length=100)
    config.Set("AdminUI.csrf_secret_key", key)
  else:
    print("Not updating csrf key as it is already set.")


def GenerateKeys(config, overwrite_keys=False):
  """Generate the keys we need for a GRR server."""
  if not hasattr(key_utils, "MakeCACert"):
    raise OpenSourceKeyUtilsRequiredError(
        "Generate keys can only run with open source key_utils.")
  if (config.Get("PrivateKeys.server_key", default=None) and
      not overwrite_keys):
    print(config.Get("PrivateKeys.server_key"))
    raise KeysAlreadyExistError(
        "Config %s already has keys, use --overwrite_keys to "
        "override." % config.parser)

  length = grr_config.CONFIG["Server.rsa_key_length"]
  print("All keys will have a bit length of %d." % length)
  print("Generating executable signing key")
  executable_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  config.Set("PrivateKeys.executable_signing_private_key",
             executable_key.AsPEM())
  config.Set("Client.executable_signing_public_key",
             executable_key.GetPublicKey().AsPEM())

  print("Generating CA keys")
  ca_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  ca_cert = key_utils.MakeCACert(ca_key)
  config.Set("CA.certificate", ca_cert.AsPEM())
  config.Set("PrivateKeys.ca_key", ca_key.AsPEM())

  print("Generating Server keys")
  server_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  server_cert = key_utils.MakeCASignedCert(u"grr", server_key, ca_cert, ca_key)
  config.Set("Frontend.certificate", server_cert.AsPEM())
  config.Set("PrivateKeys.server_key", server_key.AsPEM())

  print("Generating secret key for csrf protection.")
  _GenerateCSRFKey(config)
