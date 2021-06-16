#!/usr/bin/env python
"""A module with YARA convenience wrappers for the GRR API."""

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
  if not isinstance(response, yara_pb2.ApiUploadYaraSignatureResult):
    raise TypeError(f"Unexpected response type: {type(response)}")

  return response.blob_id
