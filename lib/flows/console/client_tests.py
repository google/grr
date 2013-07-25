#!/usr/bin/env python
"""This defines some tests for real world clients to be run from the console."""



import os
import re
import unittest


from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.console import debugging


def TestFlows(client_id, platform, testname=None, local_worker=False):
  """Test a bunch of flows."""

  if platform not in ["windows", "linux", "darwin"]:
    raise RuntimeError("Requested operating system not supported.")

  # This token is not really used since there is no approval for the
  # tested client - these tests are designed for raw access - but we send it
  # anyways to have an access reason.
  token = access_control.ACLToken("test", "client testing")

  client_id = rdfvalue.RDFURN(client_id)
  RunTests(client_id, platform=platform, testname=testname,
           token=token, local_worker=local_worker)


class ClientTestBase(test_lib.GRRBaseTest):
  """This is the base class for all client tests."""
  platforms = []
  flow = None
  args = {}
  cpu_limit = None
  network_bytes_limit = None

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, client_id=None, platform=None, local_worker=False,
               token=None):
    # If we get passed a string, turn it into a urn.
    self.client_id = rdfvalue.RDFURN(client_id)
    self.platform = platform
    self.token = token
    self.local_worker = local_worker
    super(ClientTestBase, self).__init__(methodName="runTest")

  def setUp(self):
    # Disable setUp since the cleanup between unit tests does not make sense
    # here.
    pass

  def tearDown(self):
    # Disable tearDown since the cleanup between unit tests does not make sense
    # here.
    pass

  def runTest(self):
    if self.local_worker:
      self.flow_obj = debugging.StartFlowAndWorker(
          self.client_id, self.flow, cpu_limit=self.cpu_limit,
          network_bytes_limit=self.network_bytes_limit, **self.args)
    else:
      self.flow_obj = debugging.StartFlowAndWait(
          self.client_id, self.flow, cpu_limit=self.cpu_limit,
          network_bytes_limit=self.network_bytes_limit, **self.args)

    self.CheckFlow()

  def CheckFlow(self):
    pass

  def DeleteUrn(self, urn):
    """Deletes an object from the db and the index, and flushes the caches."""
    data_store.DB.DeleteSubject(urn, token=self.token)
    aff4.FACTORY._DeleteChildFromIndex(urn, token=self.token)
    aff4.FACTORY.Flush()

  def GetGRRBinaryName(self, run_interrogate=True):
    client = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.assertIsInstance(client, aff4.VFSGRRClient)
    config = client.Get(aff4.VFSGRRClient.SchemaCls.GRR_CONFIGURATION)

    if config is None:
      # Try running Interrogate once.
      if run_interrogate:
        debugging.StartFlowAndWait(self.client_id, "Interrogate")
        return self.GetGRRBinaryName(run_interrogate=False)
      else:
        self.fail("No valid configuration found, interrogate the client before "
                  "running this test.")
    else:
      self.binary_name = config["Client.binary_name"]
      return self.binary_name


class LocalClientTest(ClientTestBase):

  def runTest(self):
    if not self.local_worker:
      print ("This test uses a flow that is debug only. Use a local worker"
             " to run this test.")
      return
    super(LocalClientTest, self).runTest()


class TestGetFileTSKLinux(ClientTestBase):
  """Tests if GetFile works on Linux using Sleuthkit."""
  platforms = ["linux"]

  flow = "GetFile"
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin/ls",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}

  # Interpolate for /dev/mapper-...
  output_path = "/fs/tsk/.*/bin/ls"

  def CheckFlow(self):
    pos = self.output_path.find("*")
    if pos > 0:
      urn = self.client_id.Add(self.output_path[:pos])
      for entry in data_store.DB.Query(subject_prefix=urn):
        subject = entry["subject"][0][0]
        if re.search(self.output_path + "$", subject):
          urn = subject
          self.to_delete = rdfvalue.RDFURN(urn)
          return self.CheckFile(aff4.FACTORY.Open(urn))
    else:
      urn = self.client_id.Add(self.output_path)
      fd = aff4.FACTORY.Open(urn)
      if isinstance(fd, aff4.HashImage):
        return self.CheckFile(fd)

    self.fail("Output file not found.")

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[1:4], "ELF")

  def tearDown(self):
    super(TestGetFileTSKLinux, self).tearDown()
    if hasattr(self, "to_delete"):
      urn = self.to_delete
    else:
      urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(urn)
    # Make sure the deletion acutally worked.
    self.assertRaises(AssertionError, self.CheckFlow)


class TestGetFileTSKMac(TestGetFileTSKLinux):
  """Tests if GetFile works on Mac using Sleuthkit."""
  platforms = ["darwin"]

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[:4], "\xca\xfe\xba\xbe")


class TestGetFileOSLinux(TestGetFileTSKLinux):
  """Tests if GetFile works on Linux."""
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin/ls",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  output_path = "/fs/os/bin/ls"


class TestListDirectoryOSLinux(ClientTestBase):
  """Tests if ListDirectory works on Linux."""
  platforms = ["linux", "darwin"]
  flow = "ListDirectory"
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin",
      pathtype=rdfvalue.PathSpec.PathType.OS)}

  output_path = "/fs/os/bin"
  file_to_find = "ls"

  def CheckFlow(self):
    pos = self.output_path.find("*")
    urn = None
    if pos > 0:
      base_urn = self.client_id.Add(self.output_path[:pos])
      for entry in data_store.DB.Query(subject_prefix=base_urn):
        subject = entry["subject"][0][0]
        if re.search(self.output_path + "$", subject):
          urn = rdfvalue.RDFURN(subject)
          self.to_delete = urn
          break
      self.assertNotEqual(urn, None, "Could not locate Directory.")
    else:
      urn = self.client_id.Add(self.output_path)

    fd = aff4.FACTORY.Open(urn.Add(self.file_to_find),
                           mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.VFSFile)

  def tearDown(self):
    super(TestListDirectoryOSLinux, self).tearDown()
    if hasattr(self, "to_delete"):
      urn = self.to_delete
    else:
      urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(urn.Add(self.file_to_find))
    self.DeleteUrn(urn)
    # Make sure the deletion acutally worked.
    self.assertRaises(AssertionError, self.CheckFlow)


class TestListDirectoryTSKLinux(TestListDirectoryOSLinux):
  """Tests if ListDirectory works on Linux using Sleuthkit."""
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}
  output_path = "/fs/tsk/.*/bin"


class TestFindTSKLinux(TestListDirectoryTSKLinux):
  """Tests if the find flow works on Linux using Sleuthkit."""
  flow = "FindFiles"

  args = {"findspec": rdfvalue.RDFFindSpec(
      pathspec=rdfvalue.PathSpec(
          path="/bin",
          pathtype=rdfvalue.PathSpec.PathType.TSK))}


class TestFindOSLinux(TestListDirectoryOSLinux):
  """Tests if the find flow works on Linux."""
  flow = "FindFiles"

  args = {"findspec": rdfvalue.RDFFindSpec(
      pathspec=rdfvalue.PathSpec(
          path="/bin",
          pathtype=rdfvalue.PathSpec.PathType.OS))}


class TestInterrogate(ClientTestBase):
  """Tests the Interrogate flow on windows."""
  platforms = ["windows", "linux", "darwin"]
  flow = "Interrogate"

  attributes = [aff4.VFSGRRClient.SchemaCls.GRR_CONFIGURATION,
                aff4.VFSGRRClient.SchemaCls.MAC_ADDRESS,
                aff4.VFSGRRClient.SchemaCls.HOSTNAME,
                aff4.VFSGRRClient.SchemaCls.INSTALL_DATE,
                aff4.VFSGRRClient.SchemaCls.CLIENT_INFO,
                aff4.VFSGRRClient.SchemaCls.OS_RELEASE,
                aff4.VFSGRRClient.SchemaCls.OS_VERSION,
                aff4.VFSGRRClient.SchemaCls.USERNAMES]

  def setUp(self):
    super(TestInterrogate, self).setUp()
    data_store.DB.DeleteAttributes(self.client_id, [
        str(attribute) for attribute in self.attributes], sync=True)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    fd = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.assertIsInstance(fd, aff4.VFSGRRClient)
    for attribute in self.attributes:
      value = fd.Get(attribute)
      self.assertTrue(value is not None, "Attribute %s is None." % attribute)
      self.assertTrue(str(value))


class TestListDirectoryOSWindows(TestListDirectoryOSLinux):
  """Tests if ListDirectory works on Linux."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  file_to_find = "regedit.exe"
  output_path = "/fs/os/C:/Windows"


class TestListDirectoryTSKWindows(TestListDirectoryTSKLinux):
  """Tests if ListDirectory works on Windows using Sleuthkit."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}
  file_to_find = "regedit.exe"

  def CheckFlow(self):
    # XP has uppercase...
    for windir in ["Windows", "WINDOWS"]:
      urn = self.client_id.Add("/fs/tsk")
      fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
      volumes = list(fd.OpenChildren())
      found = False
      for volume in volumes:
        fd = aff4.FACTORY.Open(volume.urn.Add(windir), mode="r",
                               token=self.token)
        children = list(fd.OpenChildren())
        for child in children:
          if self.file_to_find == child.urn.Basename():
            # We found what we were looking for.
            found = True
            self.to_delete = child.urn
            break
    self.assertTrue(found)


class TestRecursiveListDirectoryOSWindows(TestListDirectoryOSWindows):
  flow = "RecursiveListDirectory"
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\",
      pathtype=rdfvalue.PathSpec.PathType.OS),
          "max_depth": 1}
  file_to_find = "regedit.exe"
  output_path = "/fs/os/C:/Windows"


class TestFindWindowsRegistry(ClientTestBase):
  """Test that user listing from the registry works.

  We basically list the registry and then run Find on the same place, we expect
  a single ProfileImagePath value for each user.
  """
  platforms = ["windows"]
  reg_path = ("/HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/"
              "CurrentVersion/ProfileList")

  output_path = "analysis/find/test"

  def runTest(self):
    """Launch our flows."""
    debugging.StartFlowAndWait(self.client_id, "ListDirectory",
                               pathspec=rdfvalue.PathSpec(
                                   pathtype=rdfvalue.PathSpec.PathType.REGISTRY,
                                   path=self.reg_path))

    debugging.StartFlowAndWait(
        self.client_id, "FindFiles",
        findspec=rdfvalue.RDFFindSpec(
            pathspec=rdfvalue.PathSpec(
                path=self.reg_path,
                pathtype=rdfvalue.PathSpec.PathType.REGISTRY),
            path_regex="ProfileImagePath"),
        output=self.output_path)

    self.CheckFlow()

  def CheckFlow(self):
    """Check that all profiles listed have an ProfileImagePath."""
    urn = self.client_id.Add("registry").Add(self.reg_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)

    user_accounts = sorted([x.urn for x in fd.OpenChildren()
                            if x.urn.Basename().startswith("S-")])

    urn = self.client_id.Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    hits = sorted([x.urn for x in fd.OpenChildren()])

    self.assertEqual(len(hits), len(user_accounts))
    self.assertTrue(len(hits) > 1)

    for x, y in zip(user_accounts, hits):
      self.assertEqual(x.Add("ProfileImagePath"), y)


class TestGetFileOSWindows(TestGetFileOSLinux):
  """Tests if GetFile works on Windows."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  output_path = "/fs/os/C:/Windows/regedit.exe"

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[:2], "MZ")


class TestGetFileTSKWindows(TestGetFileOSWindows):
  """Tests if GetFile works on Windows using TSK."""
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}

  def CheckFlow(self):
    urn = self.client_id.Add("/fs/tsk")
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    volumes = list(fd.OpenChildren())
    found = False
    for volume in volumes:
      file_urn = volume.urn.Add("Windows/regedit.exe")
      fd = aff4.FACTORY.Open(file_urn, mode="r",
                             token=self.token)
      try:
        data = fd.Read(10)
        if data[:2] == "MZ":
          found = True
          self.to_delete = file_urn
          break
      except AttributeError:
        # If the file does not exist on this volume, Open returns a aff4volume
        # which does not have a Read method.
        pass
    self.assertTrue(found)


class TestRegistry(ClientTestBase):
  """Tests if listing registry keys works on Windows."""
  platforms = ["windows"]
  flow = "ListDirectory"

  args = {"pathspec": rdfvalue.PathSpec(
      path="HKEY_LOCAL_MACHINE",
      pathtype=rdfvalue.PathSpec.PathType.REGISTRY)}
  output_path = "/registry/HKEY_LOCAL_MACHINE"

  def CheckFlow(self):
    urn = self.client_id.Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    children = list(fd.OpenChildren())
    self.assertTrue("SYSTEM" in [os.path.basename(utils.SmartUnicode(child.urn))
                                 for child in children])

  def tearDown(self):
    urn = self.client_id.Add(self.output_path)
    data_store.DB.DeleteSubject(str(urn.Add("SYSTEM")), token=self.token)
    data_store.DB.DeleteSubject(str(urn), token=self.token)


def RunTests(client_id=None, platform=None, testname=None,
             token=None, local_worker=False):
  runner = unittest.TextTestRunner()
  for cls in ClientTestBase.classes.values():
    if testname is not None and testname != cls.__name__:
      continue

    if not aff4.issubclass(cls, ClientTestBase):
      continue

    if platform in cls.platforms:
      print "Running %s." % cls.__name__
      runner.run(cls(client_id=client_id, platform=platform,
                     token=token, local_worker=local_worker))


class TestCPULimit(LocalClientTest):
  platforms = ["linux", "windows", "darwin"]

  flow = "CPULimitTestFlow"

  cpu_limit = 7

  def CheckFlow(self):
    backtrace = self.flow_obj.state.context.get("backtrace", "")
    if "BusyHang not available" in backtrace:
      print "Client does not support this test."
    else:
      self.assertTrue("CPU limit exceeded." in backtrace)


class TestNetworkFlowLimit(ClientTestBase):
  platforms = ["linux", "darwin"]
  flow = "GetFile"
  network_bytes_limit = 2 * 1024 * 1024
  args = {"pathspec": rdfvalue.PathSpec(path="/usr/bin/python",
                                        pathtype=rdfvalue.PathSpec.PathType.OS)}

  output_path = "/fs/os/usr/bin/python"

  def setUp(self):
    self.urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(self.urn)
    fd = aff4.FACTORY.Open(self.urn, mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.AFF4Volume)

  def CheckFlow(self):
    self.assertAlmostEqual(self.flow_obj.state.context.network_bytes_sent,
                           self.network_bytes_limit, delta=3000)
    backtrace = self.flow_obj.state.context.get("backtrace", "")
    self.assertTrue("Network bytes limit exceeded." in backtrace)

    fd = aff4.FACTORY.Open(self.urn, mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.AFF4Volume)


class TestFastGetFileNetworkLimitExceeded(LocalClientTest):
  platforms = ["linux", "darwin"]
  flow = "NetworkLimitTestFlow"
  args = {}
  network_bytes_limit = 3 * 512 * 1024

  def CheckFlow(self):
    backtrace = self.flow_obj.state.context.get("backtrace", "")
    self.assertTrue("Network bytes limit exceeded." in backtrace)

    self.output_path = self.flow_obj.state.dest_path.path
    self.urn = self.client_id.Add(self.output_path)

    fd = aff4.FACTORY.Open(self.urn, mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.AFF4Volume)


class TestFastGetFile(LocalClientTest):
  platforms = ["linux", "darwin"]
  flow = "FastGetFileTestFlow"
  args = {}

  def CheckFlow(self):
    # Check flow completed normally, checking is done inside the flow
    self.assertEqual(self.flow_obj.state.context.state,
                     rdfvalue.Flow.State.TERMINATED)
    self.assertFalse(self.flow_obj.state.context.get("backtrace", ""))


class TestProcessListing(ClientTestBase):
  platforms = ["linux", "windows", "darwin"]

  flow = "ListProcesses"

  def setUp(self):
    super(TestProcessListing, self).setUp()
    self.process_urn = self.client_id.Add("processes")
    self.DeleteUrn(self.process_urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    procs = aff4.FACTORY.Open(self.process_urn, mode="r", token=self.token)
    self.assertIsInstance(procs, aff4.ProcessListing)
    process_list = procs.Get(procs.Schema.PROCESSES)
    # Make sure there are at least some results.
    self.assertGreater(len(process_list), 5)

    expected_name = self.GetGRRBinaryName()
    for p in process_list:
      if expected_name in p.exe:
        return
    self.fail("Process listing does not contain %s." % expected_name)


class TestNetstat(ClientTestBase):
  platforms = ["linux", "windows", "darwin"]

  flow = "Netstat"

  def setUp(self):
    super(TestNetstat, self).setUp()
    self.network_urn = self.client_id.Add("network")
    self.DeleteUrn(self.network_urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    netstat = aff4.FACTORY.Open(self.network_urn, mode="r", token=self.token)
    self.assertIsInstance(netstat, aff4.Network)
    connections = netstat.Get(netstat.Schema.CONNECTIONS)
    self.assertGreater(len(connections), 5)
    # There should be at least two local IPs.
    num_ips = set([k.local_address.ip for k in connections])
    self.assertGreater(len(num_ips), 1)
    # There should be at least two different connection states.
    num_states = set([k.state for k in connections])
    self.assertGreater(len(num_states), 1)


class TestGetClientStats(ClientTestBase):
  platforms = ["linux", "windows", "darwin"]

  flow = "GetClientStats"

  def setUp(self):
    super(TestGetClientStats, self).setUp()
    self.stats_urn = self.client_id.Add("stats")
    self.DeleteUrn(self.stats_urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    client_stats = aff4.FACTORY.Open(self.stats_urn, token=self.token)
    self.assertIsInstance(client_stats, aff4.ClientStats)

    stats = list(client_stats.Get(client_stats.Schema.STATS))
    self.assertGreater(len(stats), 0)
    entry = stats[0]
    self.assertGreater(entry.RSS_size, 0)
    self.assertGreater(entry.VMS_size, 0)
    self.assertGreater(entry.boot_time, 0)
    self.assertGreater(entry.bytes_received, 0)
    self.assertGreater(entry.bytes_sent, 0)
    self.assertGreater(entry.memory_percent, 0)

    self.assertGreater(len(list(entry.io_samples)), 0)
    self.assertGreater(len(list(entry.cpu_samples)), 0)


class FingerPrintTestBase(object):
  flow = "FingerprintFile"

  def setUp(self):
    self.urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(self.urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    fd = aff4.FACTORY.Open(self.urn)
    fp = fd.Get(fd.Schema.FINGERPRINT)
    self.assertNotEqual(fp, None)
    results = list(fp.results)
    self.assertGreater(len(results), 0)

    result = results[0]
    self.assertTrue("md5" in result)
    self.assertEqual(len(result["md5"]), 16)
    self.assertTrue("sha1" in result)
    self.assertEqual(len(result["sha1"]), 20)
    self.assertTrue("sha256" in result)
    self.assertEqual(len(result["sha256"]), 32)


class TestFingerprintFileOSLinux(FingerPrintTestBase, TestGetFileOSLinux):
  """Tests if Fingerprinting works on Linux."""


class TestFingerprintFileOSWindows(FingerPrintTestBase, TestGetFileOSWindows):
  """Tests if Fingerprinting works on Windows."""


class TestAnalyzeClientMemory(ClientTestBase):
  platforms = ["windows"]
  flow = "AnalyzeClientMemory"
  args = {"plugins": "pslist",
          "output": "analysis/pslist/testing"}

  def setUp(self):
    super(TestAnalyzeClientMemory, self).setUp()
    self.urn = self.client_id.Add(self.args["output"])
    self.DeleteUrn(self.urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.urn, token=self.token)
    self.assertIsInstance(response, aff4.VolatilityResponse)
    result = response.Get(response.Schema.RESULT)
    self.assertEqual(result.error, "")
    self.assertGreater(len(result.sections), 0)

    rows = result.sections[0].table.rows
    self.assertGreater(len(rows), 0)

    expected_name = self.GetGRRBinaryName()
    for values in rows:
      for value in values.values:
        if value.name == "ImageFileName":
          if expected_name == value.svalue:
            return

    self.fail("Process listing does not contain %s." % expected_name)


class TestGrepMemory(ClientTestBase):
  platforms = ["windows"]
  flow = "GrepMemory"

  args = {"output": "analysis/grep/testing",
          "request": rdfvalue.GrepSpec(
              literal="grr", length=4*1024*1024*1024,
              mode=rdfvalue.GrepSpec.Mode.FIRST_HIT,
              bytes_before=10, bytes_after=10)}

  def setUp(self):
    super(TestGrepMemory, self).setUp()
    self.urn = self.client_id.Add(self.args["output"])
    self.DeleteUrn(self.urn)
    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(self.urn, token=self.token)
    self.assertIsInstance(collection, aff4.GrepResultsCollection)
    self.assertEqual(len(list(collection)), 1)
    reference = collection[0]

    self.assertEqual(reference.length, 23)
    self.assertEqual(reference.data[10:10+3], "grr")


class TestLaunchBinaries(ClientTestBase):
  """Test that we can launch a binary.

  The following program is used and will be signed and uploaded before
  executing the test if it hasn't been uploaded already.

  #include <stdio.h>
  int main(int argc, char** argv) {
    printf("Hello world!!!");
    return 0;
  };
  """
  platforms = ["windows", "linux"]
  flow = "LaunchBinary"
  filenames = {"windows": "hello.exe",
               "linux": "hello"}

  def __init__(self, **kwargs):
    super(TestLaunchBinaries, self).__init__(**kwargs)
    self.context = ["Platform:%s" % self.platform.title()]
    self.binary = config_lib.CONFIG.Get(
        "Executables.aff4_path", context=self.context).Add(
            "test/%s" % self.filenames[self.platform])

    self.args = dict(binary=self.binary)

    try:
      aff4.FACTORY.Open(self.binary, aff4_type="GRRSignedBlob",
                        token=self.token)
    except IOError:
      print "Uploading the test binary to the Executables area."
      source = os.path.join(config_lib.CONFIG["Test.data_dir"],
                            self.filenames[self.platform])

      maintenance_utils.UploadSignedConfigBlob(
          open(source, "rb").read(), aff4_path=self.binary,
          client_context=self.context, token=self.token)

  def CheckFlow(self):
    # Check that the test binary returned the correct stdout:
    fd = aff4.FACTORY.Open(self.flow_obj.urn, age=aff4.ALL_TIMES,
                           token=self.token)
    logs = "\n".join(
        [str(x) for x in fd.GetValuesForAttribute(fd.Schema.LOG)])

    self.assertTrue("Hello world" in logs)
