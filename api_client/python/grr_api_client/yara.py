#!/usr/bin/env python
"""A module with YARA convenience wrappers for the GRR API."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Text

from grr_api_client import context as api_context
from grr_response_proto.api import yara_pb2


def UploadYaraSignature(
    signature: Text,
    context: api_context.GrrApiContext,
) -> bytes:
  """Uploads the specified YARA signature.

  Args:
    signature: A YARA signature to upload.
    context: An GRR API context object.

  Returns:
    A reference to the uploaded blob.
  """
  args = yara_pb2.ApiUploadYaraSignatureArgs(signature=signature)

  response = context.SendRequest("UploadYaraSignature", args)
  return response.blob_id
