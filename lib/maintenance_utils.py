#!/usr/bin/env python

# Copyright 2012 Google Inc.
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


"""This file contains utility classes related to maintenance used by GRR."""



import hashlib
import os


from M2Crypto import BIO
from M2Crypto import RSA

import logging

from grr.lib import aff4
from grr.lib import utils
from grr.proto import jobs_pb2

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"

MAX_FILE_SIZE = 1024*1024*10  # 10MB


def UploadSignedConfigBlob(file_obj, aff4_path="/config/drivers",
                           file_name=None, signing_key=None, token=None):
  """Upload a signed blob into the datastore.

  Args:
    file_obj: A file like object containing the file to upload.
    aff4_path: Path in aff4 to upload to.
    file_name: Unique name for file to upload as, if None will default to
        basename of file_obj.name.
    signing_key: A file path to a key that can be loaded to sign the data.
    token: A security token.

  Returns:
    String containing path the file was written to.

  Raises:
    IOError: On bad key.
  """
  if not file_name:
    file_name = os.path.basename(file_obj.name)
  path = utils.JoinPath(aff4_path, file_name)
  fd = aff4.FACTORY.Create(path, "GRRSignedBlob", token=token)

  pb = jobs_pb2.SignedDriver()
  data = file_obj.read(MAX_FILE_SIZE)

  digest = DIGEST_ALGORITHM(data).digest()
  if signing_key:
    rsa = RSA.load_key(signing_key)  # will prompt for passphrase
    if len(rsa) < 2048:
      raise IOError("signing key is too short.")

    sig = rsa.sign(digest, DIGEST_ALGORITHM_STR)
    pb.signature = sig
    pb.signature_type = pb.RSA_2048

  pb.digest = digest
  pb.digest_type = pb.SHA256
  pb.data = data

  # Test we can verify before we send it off.
  m = BIO.MemoryBuffer()
  rsa.save_pub_key_bio(m)
  if not VerifySignedDriver(pb, m.read_all()):
    raise IOError("Failed to verify our own signed blob")

  fd.Set(fd.Schema.DRIVER(pb))
  fd.Close()
  logging.info("Uploaded to %s", path)
  return str(fd.urn)


def VerifySignedDriver(driver_pb, pub_key):
  """Verify a key, returns True or False."""
  bio = BIO.MemoryBuffer(pub_key)
  rsa = RSA.load_pub_key_bio(bio)
  result = 0
  try:
    result = rsa.verify(driver_pb.digest, driver_pb.signature,
                        DIGEST_ALGORITHM_STR)
  except RSA.RSAError:
    logging.warn("Could not verify driver.")
    return False
  digest = hashlib.sha256(driver_pb.data).digest()
  if digest != driver_pb.digest:
    logging.warn("Driver digest sent in proto did not match actual data.")
    return False

  return result == 1
