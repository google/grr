#!/usr/bin/env python
"""Utilities for generating GRR keys as part of config_updater run."""

from grr_response_core import config as grr_config
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto


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
    key = utils.GeneratePassphrase(length=100)
    config.Set("AdminUI.csrf_secret_key", key)
  else:
    print("Not updating csrf key as it is already set.")


def GenerateKeys(config, overwrite_keys=False):
  """Generate the keys we need for a GRR server."""

  if (
      config.Get("PrivateKeys.executable_signing_private_key", default=None)
      and not overwrite_keys
  ):
    print(config.Get("PrivateKeys.executable_signing_private_key"))
    raise KeysAlreadyExistError(
        "Config %s already has keys, use --overwrite_keys to override."
        % config.parser
    )

  length = grr_config.CONFIG["Server.rsa_key_length"]
  print("All keys will have a bit length of %d." % length)
  print("Generating executable signing key")
  executable_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  config.Set(
      "PrivateKeys.executable_signing_private_key",
      executable_key.AsPEM().decode("ascii"),
  )
  config.Set(
      "Client.executable_signing_public_key",
      executable_key.GetPublicKey().AsPEM().decode("ascii"),
  )

  print("Generating secret key for csrf protection.")
  _GenerateCSRFKey(config)
