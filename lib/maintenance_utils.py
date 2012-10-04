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


from M2Crypto import BIO
from M2Crypto import RSA

import logging

from grr.lib import aff4
from grr.lib import data_store
from grr.proto import jobs_pb2

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"

SUPPORTED_PLATFORMS = ["windows", "linux", "osx"]


def SignConfigBlob(blob_data, signing_key=None):
  """Upload a signed blob into the datastore.

  Args:
    blob_data: String containing the blob data.
    signing_key: A key that can be loaded to sign the data as a string.

  Returns:
    A completed jobs_pb2.SignedBlob

  Raises:
    IOError: On bad key.
  """
  pb = jobs_pb2.SignedBlob()
  digest = DIGEST_ALGORITHM(blob_data).digest()
  if signing_key:
    rsa = RSA.load_key_string(signing_key)  # will prompt for passphrase
    if len(rsa) < 2048:
      raise IOError("signing key is too short.")

    sig = rsa.sign(digest, DIGEST_ALGORITHM_STR)
    pb.signature = sig
    pb.signature_type = pb.RSA_2048

  pb.digest = digest
  pb.digest_type = pb.SHA256
  pb.data = blob_data

  # Test we can verify before we send it off.
  m = BIO.MemoryBuffer()
  rsa.save_pub_key_bio(m)
  if not VerifySignedBlob(pb, m.read_all()):
    raise IOError("Failed to verify our own signed blob")

  logging.info("Successfully signed")
  return pb


def UploadSignedConfigBlob(blob_pb, file_name=None,
                           aff4_path="/config/executables", token=None):
  """Upload a signed blob into the datastore.

  Args:
    blob_pb: A completed SignedBlob protobuf.
    file_name: Unique name for file to upload as
    aff4_path: Path in aff4 to upload to.
    token: A security token.

  Returns:
    String containing path the file was written to.

  Raises:
    IOError: On failure to write.
  """
  path = aff4.RDFURN(aff4_path)
  if file_name:
    path = path.Add(file_name)
  fd = aff4.FACTORY.Create(path, "GRRSignedBlob", mode="w", token=token)
  fd.Set(fd.Schema.BINARY(blob_pb))
  fd.Close()
  logging.info("Uploaded to %s", path)
  return str(fd.urn)


def UploadSignedDriverBlob(blob_pb, file_name=None, aff4_path="/config/drivers",
                           install_request=None, token=None):
  """Upload a signed driver blob into the datastore.

  Args:
    blob_pb: A completed SignedBlob protobuf.
    file_name: Unique name for file to upload as
    aff4_path: Path in aff4 to upload to.
    install_request: A protobuf describing the installation parameters
                     for this driver.
    token: A security token.

  Returns:
    String containing path the file was written to.

  Raises:
    IOError: On failure to write driver.
  """
  path = UploadSignedConfigBlob(blob_pb, file_name=file_name,
                                aff4_path=aff4_path, token=token)
  fd = aff4.FACTORY.Open(path, required_type="GRRSignedBlob", mode="rw",
                         token=token)
  fd = fd.Upgrade("GRRMemoryDriver")
  if install_request:
    logging.info("Setting installation parameters.")
    fd.Set(fd.Schema.INSTALLATION(install_request))
  fd.Close()
  return str(fd.urn)


def VerifySignedBlob(blob_pb, pub_key):
  """Verify a key, returns True or False."""
  bio = BIO.MemoryBuffer(pub_key)
  rsa = RSA.load_pub_key_bio(bio)
  result = 0
  try:
    result = rsa.verify(blob_pb.digest, blob_pb.signature,
                        DIGEST_ALGORITHM_STR)
  except RSA.RSAError, e:
    logging.warn("Could not verify blob. Error: %s", e)
    return False
  digest = hashlib.sha256(blob_pb.data).digest()
  if digest != blob_pb.digest:
    logging.warn("Digest in proto did not match actual data.")
    return False

  return result == 1


def GetConfigBinaryPathType(aff4_path):
  """Take an aff4_path and return type or None.

  Args:
    aff4_path: An RDFURN containing the path to the binary.

  Returns:
    None if the path is not supported for binary upload, otherwise a type.
  """
  if not aff4_path.Path().startswith("/config"):
    return
  components = aff4_path.RelativeName("aff4:/config").split("/")
  if components[0] == "drivers" and components[1] in SUPPORTED_PLATFORMS:
    return "GRRMemoryDriver"
  elif components[0] == "executables" and components[1] in SUPPORTED_PLATFORMS:
    return "GRRSignedBlob"
  elif components[0] == "python_hacks":
    return "GRRSignedBlob"
  else:
    return


def CreateBinaryConfigPaths():
  """Create the paths required for binary configs."""
  required_dirs = set(["drivers", "executables", "python_hacks"])

  try:
    config_obj = aff4.FACTORY.Open("aff4:/config", required_type="AFF4Volume")
    dirs = set(d.Basename() for d in config_obj.ListChildren())
    for req_dir in required_dirs:
      if req_dir not in dirs:
        aff4.FACTORY.Create("aff4:/config/%s" % req_dir, "AFF4Volume").Flush()
    if not dirs:
      # We weren't already initialized, create all directories.
      for platform in SUPPORTED_PLATFORMS:
        aff4.FACTORY.Create("aff4:/config/drivers/%s/memory" % platform,
                            "AFF4Volume").Flush()
      for platform in SUPPORTED_PLATFORMS:
        aff4.FACTORY.Create("aff4:/config/executables/%s/agentupdates"
                            % platform, "AFF4Volume").Flush()
        aff4.FACTORY.Create("aff4:/config/executables/%s/installers"
                            % platform, "AFF4Volume").Flush()

  except data_store.UnauthorizedAccess:
    logging.info("User is not admin, cannot check configuration tree.")
    return
