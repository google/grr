#!/usr/bin/env python
"""End to end tests for lib.flows.general.transfer."""

import hashlib
import socket
import threading


from grr.client.client_actions import standard
from grr.endtoend_tests import base
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2
from grr.server import aff4
from grr.server import flow
from grr.server.aff4_objects import aff4_grr
from grr.server.flows.general import fingerprint
from grr.server.flows.general import transfer


class MultiGetFileTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MultiGetFileTestFlowArgs


class MultiGetFileTestFlow(flow.GRRFlow):
  """This flow checks MultiGetFile correctly transfers files."""
  args_type = MultiGetFileTestFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Create some files to transfer.

    Using /dev/urandom ensures the file actually gets transferred and we don't
    just test the cache. The files created on the client will be automatically
    deleted.  If you need the client files for debugging, remove the lifetime
    parameter from CopyPathToFile.
    """
    self.state.client_hashes = {}
    urandom = rdf_paths.PathSpec(
        path="/dev/urandom", pathtype=rdf_paths.PathSpec.PathType.OS)

    for _ in range(self.args.file_limit):
      self.CallClient(
          standard.CopyPathToFile,
          offset=0,
          length=2 * 1024 * 1024,  # 4 default sized blobs
          src_path=urandom,
          dest_dir="",
          gzip_output=False,
          lifetime=600,
          next_state="HashFile")

  @flow.StateHandler()
  def HashFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.CallFlow(
          fingerprint.FingerprintFile.__name__,
          next_state=transfer.MultiGetFile.__name__,
          pathspec=response.dest_path,
          request_data={"pathspec": response.dest_path})

  @flow.StateHandler()
  def MultiGetFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    for response in responses:
      fd = aff4.FACTORY.Open(
          response.file_urn, aff4_grr.VFSFile, mode="r", token=self.token)
      binary_hash = fd.Get(fd.Schema.HASH)
      hash_digest = str(binary_hash.sha256)
      self.state.client_hashes[str(response.file_urn)] = hash_digest
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=[responses.request_data["pathspec"]],
          next_state="VerifyHashes")

  @flow.StateHandler()
  def VerifyHashes(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    for response in responses:
      aff4path = response.pathspec.AFF4Path(self.client_id)
      fd = aff4.FACTORY.Open(
          aff4path, aff4_grr.VFSBlobImage, mode="r", token=self.token)
      server_hash = hashlib.sha256(fd.Read(response.st_size)).hexdigest()
      client_hash = self.state.client_hashes[aff4path]

      if server_hash != client_hash:
        format_string = ("Hash mismatch server hash: %s doesn't match"
                         "client hash: %s for file: %s")
        raise flow.FlowError(format_string % (server_hash, client_hash,
                                              aff4path))


class TestMultiGetFile(base.AutomatedTest):
  platforms = ["Linux", "Darwin"]
  flow = MultiGetFileTestFlow.__name__
  args = {}

  def CheckFlow(self):
    # Reopen the object to update the state. Ignore the cache to avoid a race
    # where the flow has just been terminated but we get the cached object back
    # from the factory and it looks like it's still running.
    flow_obj = aff4.FACTORY.Open(
        self.session_id, token=self.token, aff4_type=MultiGetFileTestFlow)

    # Check flow completed normally, checking is done inside the flow
    runner = flow_obj.GetRunner()
    self.assertFalse(runner.context.backtrace)
    self.assertEqual(
        runner.GetState(), rdf_flows.FlowContext.State.TERMINATED,
        "Expected TERMINATED state, got %s" % flow_obj.context.state)


#########
# Linux #
#########


class TestGetFileTSKLinux(base.VFSPathContentIsELF):
  """Tests if GetFile works on Linux using Sleuthkit."""
  platforms = ["Linux"]
  flow = transfer.GetFile.__name__
  args = {
      "pathspec":
          rdf_paths.PathSpec(
              path="/usr/bin/diff", pathtype=rdf_paths.PathSpec.PathType.TSK)
  }
  # Interpolate for /dev/mapper-...
  test_output_path = "/fs/tsk/.*/usr/bin/diff"


class TestMultiGetFileTSKLinux(base.VFSPathContentIsELF):
  """Tests if MultiGetFile works on Linux using Sleuthkit."""
  platforms = ["Linux"]
  flow = transfer.MultiGetFile.__name__
  args = {
      "pathspecs": [
          rdf_paths.PathSpec(
              path="/usr/bin/diff", pathtype=rdf_paths.PathSpec.PathType.TSK)
      ]
  }
  test_output_path = "/fs/tsk/.*/usr/bin/diff"


class TestGetFileOSLinux(base.VFSPathContentIsELF):
  """Tests if GetFile works on Linux."""
  platforms = ["Linux"]
  flow = transfer.GetFile.__name__
  args = {
      "pathspec":
          rdf_paths.PathSpec(
              path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)
  }
  test_output_path = "/fs/os/bin/ls"


class TestMultiGetFileOSLinux(base.VFSPathContentIsELF):
  """Tests if MultiGetFile works on Linux."""
  platforms = ["Linux"]
  flow = transfer.MultiGetFile.__name__
  args = {
      "pathspecs": [
          rdf_paths.PathSpec(
              path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)
      ]
  }
  test_output_path = "/fs/os/bin/ls"


class TestSendFile(base.LocalClientTest):
  """Test SendFile.

  This test only works if your client is running on the same machine as the
  server.
  """
  platforms = ["Linux"]
  flow = transfer.SendFile.__name__
  key = rdf_crypto.AES128Key.FromHex("1a5eafcc77d428863d4c2441ea26e5a5")
  iv = rdf_crypto.AES128Key.FromHex("2241b14c64874b1898dad4de7173d8c0")

  args = dict(
      host="127.0.0.1",
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
      cipher = rdf_crypto.AES128CBCCipher(key=self.key, iv=self.iv)
      received_data = cipher.Decrypt(received_cipher)

      self.assertEqual(received_data, original_data)


##########
# Darwin #
##########


class TestGetFileOSMac(base.VFSPathContentIsMachO):
  """Tests if GetFile works on Mac."""
  platforms = ["Darwin"]
  flow = transfer.GetFile.__name__
  args = {
      "pathspec":
          rdf_paths.PathSpec(
              path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)
  }
  test_output_path = "/fs/os/bin/ls"


class TestMultiGetFileOSMac(base.VFSPathContentIsMachO):
  """Tests if MultiGetFile works on Mac."""
  platforms = ["Darwin"]
  flow = transfer.MultiGetFile.__name__
  args = {
      "pathspecs": [
          rdf_paths.PathSpec(
              path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)
      ]
  }
  test_output_path = "/fs/os/bin/ls"


###########
# Windows #
###########


class TestGetFileOSWindows(base.VFSPathContentIsPE):
  """Tests if GetFile works on Windows."""
  platforms = ["Windows"]
  flow = transfer.GetFile.__name__
  args = {
      "pathspec":
          rdf_paths.PathSpec(
              path="C:\\Windows\\regedit.exe",
              pathtype=rdf_paths.PathSpec.PathType.OS)
  }
  test_output_path = "/fs/os/C:/Windows/regedit.exe"


class TestMultiGetFileOSWindows(base.VFSPathContentIsPE):
  """Tests if MultiGetFile works on Windows."""
  platforms = ["Windows"]
  flow = transfer.MultiGetFile.__name__
  args = {
      "pathspecs": [
          rdf_paths.PathSpec(
              path="C:\\Windows\\regedit.exe",
              pathtype=rdf_paths.PathSpec.PathType.OS)
      ]
  }
  test_output_path = "/fs/os/C:/Windows/regedit.exe"


class TestGetFileTSKWindows(base.VFSPathContentIsPE):
  """Tests if GetFile works on Windows using TSK."""
  platforms = ["Windows"]
  flow = transfer.GetFile.__name__
  args = {
      "pathspec":
          rdf_paths.PathSpec(
              path="C:\\Windows\\regedit.exe",
              pathtype=rdf_paths.PathSpec.PathType.TSK)
  }
  test_output_path = "/fs/tsk/.*/Windows/regedit.exe"


class TestMultiGetFileTSKWindows(base.VFSPathContentIsPE):
  """Tests if MultiGetFile works on Windows using TSK."""
  platforms = ["Windows"]
  flow = transfer.MultiGetFile.__name__
  args = {
      "pathspecs": [
          rdf_paths.PathSpec(
              path="C:\\Windows\\regedit.exe",
              pathtype=rdf_paths.PathSpec.PathType.TSK)
      ]
  }
  test_output_path = "/fs/tsk/.*/Windows/regedit.exe"
