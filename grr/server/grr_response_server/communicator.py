#!/usr/bin/env python
"""Abstracts encryption and authentication."""

import abc
import zlib

from grr_response_core.lib import communicator
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows


Error = communicator.Error
DecodingError = communicator.Error
DecryptionError = communicator.DecryptionError
LegacyClientDecryptionError = communicator.LegacyClientDecryptionError


class Communicator(metaclass=abc.ABCMeta):
  """A class responsible for encoding and decoding comms."""

  @classmethod
  def EncodeMessageList(cls, message_list, packed_message_list):
    """Encode the MessageList into the packed_message_list rdfvalue."""
    # By default uncompress
    uncompressed_data = message_list.SerializeToBytes()
    packed_message_list.message_list = uncompressed_data

    compressed_data = zlib.compress(uncompressed_data)

    # Only compress if it buys us something.
    if len(compressed_data) < len(uncompressed_data):
      packed_message_list.compression = (
          rdf_flows.PackedMessageList.CompressionType.ZCOMPRESSION
      )
      packed_message_list.message_list = compressed_data

  @classmethod
  def DecompressMessageList(cls, packed_message_list):
    """Decompress the message data from packed_message_list.

    Args:
      packed_message_list: A PackedMessageList rdfvalue with some data in it.

    Returns:
      a MessageList rdfvalue.

    Raises:
      DecodingError: If decompression fails.
    """
    compression = packed_message_list.compression
    if compression == rdf_flows.PackedMessageList.CompressionType.UNCOMPRESSED:
      data = packed_message_list.message_list

    elif (
        compression == rdf_flows.PackedMessageList.CompressionType.ZCOMPRESSION
    ):
      try:
        data = zlib.decompress(packed_message_list.message_list)
      except zlib.error as e:
        raise DecodingError("Failed to decompress: %s" % e)
    else:
      raise DecodingError("Compression scheme not supported")

    try:
      result = rdf_flows.MessageList.FromSerializedBytes(data)
    except rdfvalue.DecodeError:
      raise DecodingError("RDFValue parsing failed.")

    return result

