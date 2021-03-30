#!/usr/bin/env python
"""A module for lazy instantiation of the GRR's Python API."""
from grr_api_client import api

from grr_colab import flags

FLAGS = flags.FLAGS

_API = None  # type: api.GrrApi


def get() -> api.GrrApi:
  """Lazily returns the GRR API object.

  This method is not thread-safe. This is okay because Colab is supposed to be
  scripted interactively and no threading is involved.

  Returns:
    A GRR API object.
  """
  global _API

  if _API is None:

    if not FLAGS.grr_http_api_endpoint:
      raise ValueError("HTTP API endpoint has not been specified.")
    if not FLAGS.grr_auth_api_user:
      raise ValueError("API user name has not been specified.")
    if not FLAGS.grr_auth_password:
      raise ValueError("API user password has not been specified.")
    auth = (FLAGS.grr_auth_api_user, FLAGS.grr_auth_password)
    _API = api.InitHttp(
        api_endpoint=FLAGS.grr_http_api_endpoint, auth=auth)

  return _API
