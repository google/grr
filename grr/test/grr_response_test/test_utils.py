#!/usr/bin/env python
"""Helper functions and classes for use by tests."""
from __future__ import absolute_import
from __future__ import division

import yaml

from grr_response_client import comms
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto


class PrivateKeyNotFoundException(Exception):

  def __init__(self):
    super(PrivateKeyNotFoundException,
          self).__init__("Private key not found in config file.")


def GetClientId(writeback_file):
  """Given the path to a client's writeback file, returns its client id."""
  with open(writeback_file) as f:
    parsed_yaml = yaml.safe_load(f.read()) or {}
  serialized_pkey = parsed_yaml.get("Client.private_key", None)
  if serialized_pkey is None:
    raise PrivateKeyNotFoundException
  pkey = rdf_crypto.RSAPrivateKey(serialized_pkey)
  client_urn = comms.ClientCommunicator(private_key=pkey).common_name
  return client_urn.Basename()
