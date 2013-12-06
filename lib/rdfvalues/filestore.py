#!/usr/bin/env python
"""FileStore-related RDFValue definitions."""

from grr.lib import aff4
from grr.lib import rdfvalue


class FileStoreHash(rdfvalue.RDFURN):
  """Urns returned from HashFileStore.ListHashes()."""

  def __init__(self, initializer=None, fingerprint_type=None, hash_type=None,
               hash_value=None, age=None):
    if fingerprint_type:
      initializer = aff4.HashFileStore.PATH.Add(fingerprint_type).Add(
          hash_type).Add(hash_value)

    super(FileStoreHash, self).__init__(initializer=initializer, age=age)

    relative_name = self.RelativeName(aff4.HashFileStore.PATH)
    if not relative_name:
      raise ValueError("URN %s is not a hash file store urn. Hash file store "
                       "urn should start with %s." %
                       (str(self), str(aff4.HashFileStore.PATH)))

    relative_path = relative_name.split("/")
    if (len(relative_path) != 3 or
        relative_path[0] not in aff4.HashFileStore.FINGERPRINT_TYPES or
        relative_path[1] not in aff4.HashFileStore.HASH_TYPES):
      raise ValueError(
          "URN %s is not a hash file store urn. Hash file store urn should "
          "look like: "
          "aff4:/files/hash/[fingerprint_type]/[hash_type]/[hash_value]." %
          str(self))

    self.fingerprint_type, self.hash_type, self.hash_value = relative_path
