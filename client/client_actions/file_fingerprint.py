#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Action to fingerprint files on the client."""


import hashlib

from grr.parsers import fingerprint
from grr.client import vfs
from grr.client.client_actions import standard
from grr.lib import utils
from grr.proto import jobs_pb2


class FingerprintFile(standard.ReadBuffer):
  """Apply a set of fingerprinting methods to a file."""
  in_protobuf = jobs_pb2.FingerprintRequest
  out_protobuf = jobs_pb2.FingerprintResponse

  _hash_types = {
      jobs_pb2.FingerprintTuple.MD5: hashlib.md5,
      jobs_pb2.FingerprintTuple.SHA1: hashlib.sha1,
      jobs_pb2.FingerprintTuple.SHA256: hashlib.sha256,
  }

  _fingerprint_types = {
      jobs_pb2.FPT_GENERIC: fingerprint.Fingerprinter.EvalGeneric,
      jobs_pb2.FPT_PE_COFF: fingerprint.Fingerprinter.EvalPecoff,
  }

  def Run(self, args):
    """Fingerprint a file."""
    with vfs.VFSHandlerFactory(args.pathspec) as file_obj:
      fingerprinter = fingerprint.Fingerprinter(file_obj)
      response = jobs_pb2.FingerprintResponse()
      if args.tuples:
        tuples = args.tuples
      else:
        # There are none selected -- we will cover everything
        tuples = list()
        for k in self._fingerprint_types.iterkeys():
          tuples.append(jobs_pb2.FingerprintTuple(fp_type=k))

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
      result = fingerprinter.HashIt()
      proto_dicts = [utils.ProtoDict(r).ToProto() for r in result]
      response.fingerprint_results.extend(proto_dicts)
      self.SendReply(response)
