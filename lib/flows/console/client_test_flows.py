#!/usr/bin/env python
"""Test flows for grr.lib.flows.console.client_tests."""

import hashlib


from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info


class CPULimitTestFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  @flow.StateHandler(next_state="State1")
  def Start(self):
    self.CallClient("BusyHang", next_state="State1")

  @flow.StateHandler(next_state="Done")
  def State1(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    self.CallClient("BusyHang", next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass


class FastGetFileTestFlow(flow.GRRFlow):
  """This flow checks FastGetFile correctly transfers files."""

  flow_typeinfo = type_info.TypeDescriptorSet(

      type_info.Integer(
          name="file_limit",
          default=3,
          help=("The number of files to retrieve.")
          )
      )

  @flow.StateHandler(next_state=["HashFile"])
  def Start(self):
    """Create some files to transfer.

    Using /dev/urandom ensures the file actually gets transferred and we don't
    just test the cache. The files created on the client will be automatically
    deleted.  If you need the client files for debugging, remove the lifetime
    parameter from CopyPathToFile.
    """
    self.state.Register("client_hashes", {})
    urandom = rdfvalue.PathSpec(path="/dev/urandom",
                                pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in range(self.state.file_limit):
      self.CallClient("CopyPathToFile",
                      offset=0,
                      length=2 * 1024 * 1024,  # 4 default sized blobs
                      src_path=urandom,
                      dest_dir="",
                      gzip_output=False,
                      lifetime=60,
                      next_state="HashFile")

  @flow.StateHandler(next_state=["FastGetFile"])
  def HashFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.CallFlow("FingerprintFile", next_state="FastGetFile",
                    pathspec=response.dest_path)

  @flow.StateHandler(next_state="VerifyHashes")
  def FastGetFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    for response in responses:
      fd = aff4.FACTORY.Open(response, "VFSFile", mode="r", token=self.token)
      binary_hash = fd.Get(fd.Schema.FINGERPRINT)
      hash_digest = binary_hash.results[0].GetItem("sha256").encode("hex")
      self.state.client_hashes[str(response)] = hash_digest

      self.CallFlow("FastGetFile", pathspec=binary_hash.pathspec,
                    next_state="VerifyHashes")

  @flow.StateHandler()
  def VerifyHashes(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    for response in responses:
      fd = aff4.FACTORY.Open(response.aff4path, "HashImage",
                             mode="r", token=self.token)
      server_hash = hashlib.sha256(fd.Read(response.st_size)).hexdigest()
      client_hash = self.state.client_hashes[response.aff4path]

      if server_hash != client_hash:
        format_string = ("Hash mismatch server hash: %s doesn't match"
                         "client hash: %s for file: %s")
        raise flow.FlowError(format_string % (server_hash, client_hash,
                                              response.aff4path))


class NetworkLimitTestFlow(flow.GRRFlow):
  """This flow is used to test the network limit for fastgetfile.

  There isn't any simple way to delete the blobs and blob cache held by the
  stubbyserver between runs.  So we create a unique file each time using
  /dev/urandom.
  """

  @flow.StateHandler(next_state="FastGetFile")
  def Start(self):
    urandom = rdfvalue.PathSpec(path="/dev/urandom",
                                pathtype=rdfvalue.PathSpec.PathType.OS)
    self.CallClient("CopyPathToFile",
                    offset=0,
                    length=2 * 1024 * 1024,  # 4 default sized blobs
                    src_path=urandom,
                    dest_dir="",
                    gzip_output=False,
                    lifetime=10,
                    next_state="FastGetFile")

  @flow.StateHandler(next_state="Done")
  def FastGetFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    self.state.Register("dest_path", responses.First().dest_path)
    self.CallFlow("FastGetFile", pathspec=self.state.dest_path,
                  next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

