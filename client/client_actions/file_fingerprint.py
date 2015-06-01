#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Action to fingerprint files on the client."""


import hashlib

from grr.parsers import fingerprint
from grr.client import vfs
from grr.client.client_actions import standard
from grr.lib.rdfvalues import client as rdf_client


class Fingerprinter(fingerprint.Fingerprinter):
  """A fingerprinter with heartbeat."""

  def __init__(self, progress_cb, file_obj):
    super(Fingerprinter, self).__init__(file_obj)
    self.progress_cb = progress_cb

  def _GetNextInterval(self):
    self.progress_cb()
    return super(Fingerprinter, self)._GetNextInterval()


class FingerprintFile(standard.ReadBuffer):
  """Apply a set of fingerprinting methods to a file."""
  in_rdfvalue = rdf_client.FingerprintRequest
  out_rdfvalue = rdf_client.FingerprintResponse

  _hash_types = {
      rdf_client.FingerprintTuple.HashType.MD5: hashlib.md5,
      rdf_client.FingerprintTuple.HashType.SHA1: hashlib.sha1,
      rdf_client.FingerprintTuple.HashType.SHA256: hashlib.sha256,
  }

  _fingerprint_types = {
      rdf_client.FingerprintTuple.Type.FPT_GENERIC: (
          fingerprint.Fingerprinter.EvalGeneric),
      rdf_client.FingerprintTuple.Type.FPT_PE_COFF: (
          fingerprint.Fingerprinter.EvalPecoff),
  }

  def Run(self, args):
    """Fingerprint a file."""
    with vfs.VFSOpen(args.pathspec,
                     progress_callback=self.Progress) as file_obj:
      fingerprinter = Fingerprinter(self.Progress, file_obj)
      response = rdf_client.FingerprintResponse()
      response.pathspec = file_obj.pathspec
      if args.tuples:
        tuples = args.tuples
      else:
        # There are none selected -- we will cover everything
        tuples = list()
        for k in self._fingerprint_types.iterkeys():
          tuples.append(rdf_client.FingerprintTuple(fp_type=k))

      for finger in tuples:
        hashers = [self._hash_types[h] for h in finger.hashers] or None
        if finger.fp_type in self._fingerprint_types:
          invoke = self._fingerprint_types[finger.fp_type]
          res = invoke(fingerprinter, hashers)
          if res:
            response.matching_types.append(finger.fp_type)
        else:
          raise RuntimeError("Encountered unknown fingerprint type. %s" %
                             finger.fp_type)

      # Structure of the results is a list of dicts, each containing the
      # name of the hashing method, hashes for enabled hash algorithms,
      # and auxilliary data where present (e.g. signature blobs).
      # Also see Fingerprint:HashIt()
      response.results = fingerprinter.HashIt()

      # We now return data in a more structured form.
      for result in response.results:
        if result.GetItem("name") == "generic":
          for hash_type in ["md5", "sha1", "sha256"]:
            value = result.GetItem(hash_type)
            if value is not None:
              setattr(response.hash, hash_type, value)

        if result["name"] == "pecoff":
          for hash_type in ["md5", "sha1", "sha256"]:
            value = result.GetItem(hash_type)
            if value:
              setattr(response.hash, "pecoff_" + hash_type, value)

          signed_data = result.GetItem("SignedData", [])
          for data in signed_data:
            response.hash.signed_data.Append(
                revision=data[0], cert_type=data[1], certificate=data[2])

      self.SendReply(response)
