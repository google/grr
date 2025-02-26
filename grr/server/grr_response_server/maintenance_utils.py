#!/usr/bin/env python
"""This file contains utility classes related to maintenance used by GRR."""

import logging
import sys

from grr_api_client import api
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server import signed_binary_utils
from grr_response_server.bin import api_shell_raw_access_lib
from grr_response_server.gui import api_call_context
import grr_response_server.local.server_config  # pylint: disable=unused-import

SUPPORTED_PLATFORMS = ["windows", "linux", "darwin"]
SUPPORTED_ARCHITECTURES = ["i386", "amd64"]

# Batch size to use when fetching multiple items from the GRR API.
_GRR_API_PAGE_SIZE = 1000


def InitGRRRootAPI():
  """Initializes the GRR root API."""

  return api.GrrApi(
      connector=api_shell_raw_access_lib.RawConnector(
          context=api_call_context.ApiCallContext(username="GRRConfigUpdater"),
          page_size=_GRR_API_PAGE_SIZE,
      )
  ).root


def EPrint(message):
  sys.stderr.write("%s\n" % message)


def UploadSignedConfigBlob(content, aff4_path, client_context=None, limit=None):
  """Upload a signed blob into the datastore.

  Args:
    content: File content to upload.
    aff4_path: aff4 path to upload to.
    client_context: The configuration contexts to use.
    limit: The maximum size of the chunk to use.

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
      parameters="PrivateKeys.executable_signing_private_key"
  )

  signing_key = config.CONFIG.Get(
      "PrivateKeys.executable_signing_private_key", context=client_context
  )

  verification_key = config.CONFIG.Get(
      "Client.executable_signing_public_key", context=client_context
  )

  signed_binary_utils.WriteSignedBinary(
      rdfvalue.RDFURN(aff4_path),
      content,
      signing_key,
      public_key=verification_key,
      chunk_size=limit,
  )

  logging.info("Uploaded to %s", aff4_path)
