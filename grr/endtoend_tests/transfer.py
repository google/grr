#!/usr/bin/env python
"""End to end tests for lib.flows.general.transfer."""

import hashlib
import re
import socket
import threading


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import flow
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2


class MultiGetFileTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MultiGetFileTestFlowArgs


class MultiGetFileTestFlow(flow.GRRFlow):
  """This flow checks MultiGetFile correctly transfers files."""
  args_type = MultiGetFileTestFlowArgs

  @flow.StateHandler(next_state=["HashFile"])
  def Start(self):
    """Create some files to transfer.

    Using /dev/urandom ensures the file actually gets transferred and we don't
    just test the cache. The files created on the client will be automatically
    deleted.  If you need the client files for debugging, remove the lifetime
    parameter from CopyPathToFile.
    """
    self.state.Register("client_hashes", {})
    urandom = rdf_paths.PathSpec(path="/dev/urandom",
                                 pathtype=rdf_paths.PathSpec.PathType.OS)

    for _ in range(self.args.file_limit):
      self.CallClient("CopyPathToFile",
                      offset=0,
                      length=2 * 1024 * 1024,  # 4 default sized blobs
                      src_path=urandom,
                      dest_dir="",
                      gzip_output=False,
                      lifetime=600,
                      next_state="HashFile")

  @flow.StateHandler(next_state=["MultiGetFile"])
  def HashFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.CallFlow("FingerprintFile",
                    next_state="MultiGetFile",
                    pathspec=response.dest_path,
                    request_data={"pathspec": response.dest_path})

  @flow.StateHandler(next_state="VerifyHashes")
  def MultiGetFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    for response in responses:
      fd = aff4.FACTORY.Open(response.file_urn,
                             aff4_grr.VFSFile,
                             mode="r",
                             token=self.token)
      binary_hash = fd.Get(fd.Schema.HASH)
      hash_digest = str(binary_hash.sha256)
      self.state.client_hashes[str(response.file_urn)] = hash_digest
      self.CallFlow("MultiGetFile",
                    pathspecs=[responses.request_data["pathspec"]],
                    next_state="VerifyHashes")

  @flow.StateHandler()
  def VerifyHashes(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    for response in responses:
      fd = aff4.FACTORY.Open(response.aff4path,
                             aff4_grr.VFSBlobImage,
                             mode="r",
                             token=self.token)
      server_hash = hashlib.sha256(fd.Read(response.st_size)).hexdigest()
      client_hash = self.state.client_hashes[response.aff4path]

      if server_hash != client_hash:
        format_string = ("Hash mismatch server hash: %s doesn't match"
                         "client hash: %s for file: %s")
        raise flow.FlowError(format_string % (server_hash, client_hash,
                                              response.aff4path))


class TestMultiGetFile(base.AutomatedTest):
  platforms = ["Linux", "Darwin"]
  flow = "MultiGetFileTestFlow"
  args = {}

  def CheckFlow(self):
    # Reopen the object to update the state. Ignore the cache to avoid a race
    # where the flow has just been terminated but we get the cached object back
    # from the factory and it looks like it's still running.
    flow_obj = aff4.FACTORY.Open(self.session_id,
                                 token=self.token,
                                 aff4_type="MultiGetFileTestFlow",
                                 ignore_cache=True)

    # Check flow completed normally, checking is done inside the flow
    runner = flow_obj.GetRunner()
    self.assertFalse(runner.context.get("backtrace", ""))
    self.assertEqual(runner.GetState(), rdf_flows.Flow.State.TERMINATED,
                     "Expected TERMINATED state, got %s" %
                     flow_obj.state.context.state)

#########
# Linux #
#########


class TestGetFileTSKLinux(base.AutomatedTest):
  """Tests if GetFile works on Linux using Sleuthkit."""
  platforms = ["Linux"]
  flow = "GetFile"
  args = {"pathspec": rdf_paths.PathSpec(
      path="/usr/bin/diff",
      pathtype=rdf_paths.PathSpec.PathType.TSK)}

  # Interpolate for /dev/mapper-...
  test_output_path = "/fs/tsk/.*/usr/bin/diff"

  def CheckFlow(self):
    pos = self.test_output_path.find("*")
    if pos > 0:
      prefix = self.client_id.Add(self.test_output_path[:pos])
      for urn in base.RecursiveListChildren(prefix=prefix, token=self.token):
        if re.search(self.test_output_path + "$", str(urn)):
          self.delete_urns.add(urn)
          return self.CheckFile(aff4.FACTORY.Open(urn, token=self.token))

      self.fail(("Output file not found. Maybe the GRR client "
                 "is not running with root privileges?"))

    else:
      urn = self.client_id.Add(self.test_output_path)
      fd = aff4.FACTORY.Open(urn, token=self.token)
      if isinstance(fd, standard.BlobImage):
        return self.CheckFile(fd)
      self.fail("Output file %s not found." % urn)

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[1:4], "ELF")


class TestMultiGetFileTSKLinux(TestGetFileTSKLinux):
  """Tests if MultiGetFile works on Linux using Sleuthkit."""
  flow = "MultiGetFile"
  args = {"pathspecs": [rdf_paths.PathSpec(
      path="/usr/bin/diff",
      pathtype=rdf_paths.PathSpec.PathType.TSK)]}


class TestGetFileOSLinux(TestGetFileTSKLinux):
  """Tests if GetFile works on Linux."""
  args = {"pathspec": rdf_paths.PathSpec(
      path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)}
  test_output_path = "/fs/os/bin/ls"


class TestMultiGetFileOSLinux(TestGetFileOSLinux):
  """Tests if MultiGetFile works on Linux."""
  flow = "MultiGetFile"
  args = {"pathspecs": [rdf_paths.PathSpec(
      path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)]}


class TestSendFile(base.LocalClientTest):
  """Test SendFile.

  This test only works if your client is running on the same machine as the
  server.
  """
  platforms = ["Linux"]
  flow = "SendFile"
  key = rdf_crypto.AES128Key("1a5eafcc77d428863d4c2441ea26e5a5")
  iv = rdf_crypto.AES128Key("2241b14c64874b1898dad4de7173d8c0")

  args = dict(host="127.0.0.1",
              port=12345,
              pathspec=rdf_paths.PathSpec(pathtype=0, path="/bin/ls"),
              key=key,
              iv=iv)

  def setUp(self):

    class Listener(threading.Thread):
      result = []
      daemon = True

      def run(self):
        for res in socket.getaddrinfo(None, 12345, socket.AF_INET,
                                      socket.SOCK_STREAM, 0,
                                      socket.AI_ADDRCONFIG):
          af, socktype, proto, _, sa = res
          try:
            s = socket.socket(af, socktype, proto)
          except socket.error:
            s = None
            continue
          try:
            s.bind(sa)
            s.listen(1)
          except socket.error:
            s.close()
            s = None
            continue
          break
        conn, _ = s.accept()
        while 1:
          data = conn.recv(1024)
          if not data:
            break
          self.result.append(data)
        conn.close()

    self.listener = Listener()
    self.listener.start()

  def CheckFlow(self):
    if self.local_client:
      original_data = open("/bin/ls", "rb").read()
      received_cipher = "".join(self.listener.result)
      cipher = rdf_crypto.AES128CBCCipher(
          key=self.key,
          iv=self.iv,
          mode=rdf_crypto.AES128CBCCipher.OP_DECRYPT)
      received_data = cipher.Update(received_cipher) + cipher.Final()

      self.assertEqual(received_data, original_data)

##########
# Darwin #
##########


class TestMultiGetFileTSKMac(TestGetFileTSKLinux):
  """Tests if MultiGetFile works on Mac using Sleuthkit."""
  platforms = ["Darwin"]

  flow = "MultiGetFile"

  def setUp(self):
    # TODO(user): At some point we'd like GRR to also be able to correctly
    # open a pathspec that only specifies "/" and TSK. For now, this doesn't
    # work though so we try all the available devices and just make sure
    # that we can get at least one result.
    pathspecs = []
    tsk_dirs = aff4.FACTORY.Open(
        self.client_id.Add("fs/tsk/dev"),
        token=self.token).OpenChildren()

    for d in tsk_dirs:
      pathspec = d.Get(d.Schema.PATHSPEC)
      if pathspec:
        pathspec.nested_path = rdf_paths.PathSpec(
            path="/bin/ls",
            pathtype=rdf_paths.PathSpec.PathType.TSK)
        pathspecs.append(pathspec)
    if not pathspecs:
      self.fail("No suitable devices found for TSK.")

    self.args = {"pathspecs": pathspecs}

  def CheckFile(self, fd):
    self.CheckMacMagic(fd)


class TestGetFileOSMac(TestGetFileOSLinux):
  """Tests if GetFile works on Mac."""
  platforms = ["Darwin"]

  def CheckFile(self, fd):
    self.CheckMacMagic(fd)


class TestMultiGetFileOSMac(TestGetFileOSMac):
  """Tests if MultiGetFile works on Mac."""
  flow = "MultiGetFile"
  args = {"pathspecs": [rdf_paths.PathSpec(
      path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)]}

###########
# Windows #
###########


class TestGetFileOSWindows(TestGetFileOSLinux):
  """Tests if GetFile works on Windows."""
  platforms = ["Windows"]
  args = {"pathspec": rdf_paths.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdf_paths.PathSpec.PathType.OS)}
  test_output_path = "/fs/os/C:/Windows/regedit.exe"

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[:2], "MZ")


class TestMultiGetFileOSWindows(TestGetFileOSWindows):
  """Tests if MultiGetFile works on Windows."""
  flow = "MultiGetFile"
  args = {"pathspecs": [rdf_paths.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdf_paths.PathSpec.PathType.OS)]}


class TestGetFileTSKWindows(TestGetFileOSWindows):
  """Tests if GetFile works on Windows using TSK."""
  args = {"pathspec": rdf_paths.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdf_paths.PathSpec.PathType.TSK)}

  def CheckFlow(self):
    urn = self.client_id.Add("/fs/tsk")
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    volumes = list(fd.OpenChildren())
    found = False
    for volume in volumes:
      file_urn = volume.urn.Add("Windows/regedit.exe")
      fd = aff4.FACTORY.Open(file_urn, mode="r", token=self.token)
      try:
        data = fd.Read(10)
        if data[:2] == "MZ":
          found = True
          self.delete_urns.add(file_urn)
          break
      except AttributeError:
        # If the file does not exist on this volume, Open returns a aff4volume
        # which does not have a Read method.
        pass
    self.assertTrue(found)


class TestMultiGetFileTSKWindows(TestGetFileTSKWindows):
  """Tests if MultiGetFile works on Windows using TSK."""
  flow = "MultiGetFile"
  args = {"pathspecs": [rdf_paths.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdf_paths.PathSpec.PathType.TSK)]}
