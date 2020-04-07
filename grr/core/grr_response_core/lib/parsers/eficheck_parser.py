#!/usr/bin/env python
# Lint as: python3
"""Parser for eficheck output."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import parser
from grr_response_core.lib.rdfvalues import apple_firmware as rdf_apple_firmware


class EficheckCmdParser(parser.CommandParser):
  """Parser for eficheck --show-hashes."""

  output_types = [rdf_apple_firmware.EfiCollection]
  # TODO(user): Add default artifact for this parser.
  supported_artifacts = []

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the eficheck output."""
    _ = stderr, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)

    collection = rdf_apple_firmware.EfiCollection()
    # The exact number of header lines may change. So try to parse and continue
    # if that fails.
    for line in stdout.decode("utf-8").splitlines():
      cols = line.split(":")
      try:
        volume_type, flags, index, address, size, guid, hash_value = cols
        entry = rdf_apple_firmware.EfiEntry(
            volume_type=int(volume_type),
            flags=int(flags, 16),
            index=int(index, 16),
            address=int(address, 16),
            size=int(size, 16),
            guid=guid,
            hash=hash_value)
        collection.entries.append(entry)
      except ValueError:
        pass

    yield collection
