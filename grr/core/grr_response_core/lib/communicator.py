#!/usr/bin/env python
"""Abstracts encryption and authentication."""

from grr_response_core.stats import metrics


# Although these metrics are never queried on the client, removing them from the
# client code seems not worth the effort.
GRR_DECODING_ERROR = metrics.Counter("grr_decoding_error")
GRR_DECRYPTION_ERROR = metrics.Counter("grr_decryption_error")
GRR_LEGACY_CLIENT_DECRYPTION_ERROR = metrics.Counter(
    "grr_legacy_client_decryption_error"
)
GRR_RSA_OPERATIONS = metrics.Counter("grr_rsa_operations")


class Error(Exception):
  """Base class for all exceptions in this module."""


class DecodingError(Error):
  """Raised when the message failed to decrypt or decompress."""

  @GRR_DECODING_ERROR.Counted()
  def __init__(self, message):
    super().__init__(message)


class DecryptionError(DecodingError):
  """Raised when the message can not be decrypted properly."""

  @GRR_DECRYPTION_ERROR.Counted()
  def __init__(self, message):
    super().__init__(message)


class LegacyClientDecryptionError(DecryptionError):
  """Raised when old clients' messages cannot be decrypted."""

  @GRR_LEGACY_CLIENT_DECRYPTION_ERROR.Counted()
  def __init__(self, message):
    super().__init__(message)
