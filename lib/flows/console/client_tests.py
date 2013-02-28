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

"""This defines some tests for real world clients to be run from the console."""



import os
import time
import unittest


from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.aff4_objects import standard


class ClientTestBase(unittest.TestCase):
  """This is the base class for all client tests."""
  platforms = []
  flow = None
  args = {}
  cpu_limit = None

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, client_id, token=None):
    self.client_id = client_id
    self.token = token
    unittest.TestCase.__init__(self)

  def runTest(self):
    self.session_id = self.StartFlowAndWait(self.client_id, self.flow,
                                            **self.args)
    self.CheckFlow()

  def StartFlowAndWait(self, client_id, flow_name, **kwargs):
    """Launches the flow and waits for it to complete.

    Args:
      client_id: The client common name we issue the request.
      flow_name: The name of the flow to launch.
      **kwargs: passthrough to flow.

    Returns:
      A GRRFlow object.
    """
    session_id = flow.FACTORY.StartFlow(client_id, flow_name, token=self.token,
                                        cpu_limit=self.cpu_limit, **kwargs)
    while 1:
      time.sleep(1)
      rdf_flow = flow.FACTORY.FetchFlow(session_id, lock=False,
                                        token=self.token)
      if rdf_flow is None:
        continue
      if rdf_flow.state != rdfvalue.Flow.Enum("RUNNING"):
        break

    return flow.FACTORY.LoadFlow(rdf_flow)

  def CheckFlow(self):
    pass


class TestGetFileTSKLinux(ClientTestBase):
  """Tests if GetFile works on Linux using Sleuthkit."""
  platforms = ["linux"]

  flow = "GetFile"
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="/bin/ls",
      pathtype=rdfvalue.RDFPathSpec.Enum("TSK"))}

  output_path = "/fs/tsk/bin/ls"

  def CheckFlow(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    self.assertEqual(type(fd), standard.HashImage)
    self.CheckFile(fd)

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[1:4], "ELF")

  def TearDown(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    data_store.DB.DeleteSubject(str(urn), token=self.token)


class TestGetFileTSKMac(TestGetFileTSKLinux):
  """Tests if GetFile works on Mac using Sleuthkit."""
  platforms = ["darwin"]

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[:4], "\xca\xfe\xba\xbe")


class TestGetFileOSLinux(TestGetFileTSKLinux):
  """Tests if GetFile works on Linux."""
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="/bin/ls",
      pathtype=rdfvalue.RDFPathSpec.Enum("OS"))}
  output_path = "/fs/os/bin/ls"


class TestListDirectoryOSLinux(ClientTestBase):
  """Tests if ListDirectory works on Linux."""
  platforms = ["linux", "darwin"]
  flow = "ListDirectory"
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="/bin",
      pathtype=rdfvalue.RDFPathSpec.Enum("OS"))}

  output_path = "/fs/os/bin"
  file_to_find = "ls"

  def CheckFlow(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    children = list(fd.OpenChildren())
    names = [os.path.basename(utils.SmartUnicode(child.urn))
             for child in children]
    self.assertTrue(self.file_to_find in names)

  def TearDown(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    data_store.DB.DeleteSubject(str(urn.Add(self.file_to_find)),
                                token=self.token)
    data_store.DB.DeleteSubject(str(urn), token=self.token)


class TestListDirectoryTSKLinux(TestListDirectoryOSLinux):
  """Tests if ListDirectory works on Linux using Sleuthkit."""
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="/bin",
      pathtype=rdfvalue.RDFPathSpec.Enum("TSK"))}
  output_path = "/fs/tsk/bin"


class TestFindTSKLinux(TestListDirectoryTSKLinux):
  """Tests if the find flow works on Linux using Sleuthkit."""
  flow = "FindFiles"

  args = {"findspec": rdfvalue.RDFFindSpec(
      pathspec=rdfvalue.RDFPathSpec(
          path="/bin",
          pathtype=rdfvalue.RDFPathSpec.Enum("TSK")))}


class TestFindOSLinux(TestListDirectoryOSLinux):
  """Tests if the find flow works on Linux."""
  flow = "FindFiles"

  args = {"findspec": rdfvalue.RDFFindSpec(
      pathspec=rdfvalue.RDFPathSpec(
          path="/bin",
          pathtype=rdfvalue.RDFPathSpec.Enum("OS")))}


class TestInterrogateWindows(ClientTestBase):
  """Tests the Interrogate flow on windows."""
  platforms = ["windows"]
  flow = "Interrogate"
  file_to_find = "System32"
  output_path = "/fs/os/"

  def CheckFlow(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    children = [x.urn.Basename() for x in fd.OpenChildren()]
    self.assert_("C:" in children)


class TestListDirectoryOSWindows(TestListDirectoryOSLinux):
  """Tests if ListDirectory works on Linux."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.RDFPathSpec.Enum("OS"))}
  file_to_find = "System32"
  output_path = "/fs/os/C:/Windows"


class TestListDirectoryTSKWindows(TestListDirectoryTSKLinux):
  """Tests if ListDirectory works on Windows using Sleuthkit."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.RDFPathSpec.Enum("TSK"))}
  file_to_find = "System32"

  def CheckFlow(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add("/fs/tsk")
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    volumes = list(fd.OpenChildren())
    found = False
    for volume in volumes:
      fd = aff4.FACTORY.Open(volume.urn.Add("Windows"), mode="r",
                             token=self.token)
      children = list(fd.OpenChildren())
      if self.file_to_find in [os.path.basename(utils.SmartUnicode(child.urn))
                               for child in children]:
        # We found what we were looking for.
        found = True
        break
    self.assertTrue(found)


class TestRecursiveListDirectoryOSWindows(TestListDirectoryOSWindows):
  flow = "RecursiveListDirectory"
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="C:\\",
      pathtype=rdfvalue.RDFPathSpec.Enum("OS")),
          "max_depth": 1}
  file_to_find = "System32"
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
    self.StartFlowAndWait(self.client_id, "ListDirectory",
                          pathspec=rdfvalue.RDFPathSpec(
                              pathtype=rdfvalue.RDFPathSpec.Enum("REGISTRY"),
                              path=self.reg_path))

    self.StartFlowAndWait(
        self.client_id, "FindFiles",
        findspec=rdfvalue.RDFFindSpec(
            pathspec=rdfvalue.RDFPathSpec(
                path=self.reg_path,
                pathtype=rdfvalue.RDFPathSpec.Enum("REGISTRY")),
            path_regex="ProfileImagePath"),
        output=self.output_path)

    self.CheckFlow()

  def CheckFlow(self):
    """Check that all profiles listed have an ProfileImagePath."""
    urn = aff4.ROOT_URN.Add(self.client_id).Add("registry").Add(self.reg_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)

    user_accounts = sorted([x.urn for x in fd.OpenChildren()
                            if x.urn.Basename().startswith("S-")])

    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    hits = sorted([x.urn for x in fd.OpenChildren()])

    self.assertEqual(len(hits), len(user_accounts))
    self.assertTrue(len(hits) > 1)

    for x, y in zip(user_accounts, hits):
      self.assertEqual(x.Add("ProfileImagePath"), y)


class TestGetFileOSWindows(TestGetFileOSLinux):
  """Tests if GetFile works on Windows."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdfvalue.RDFPathSpec.Enum("OS"))}
  output_path = "/fs/os/C:/Windows/regedit.exe"

  def CheckFile(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[:2], "MZ")


class TestGetFileTSKWindows(TestGetFileOSWindows):
  """Tests if GetFile works on Windows using TSK."""
  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdfvalue.RDFPathSpec.Enum("TSK"))}

  def CheckFlow(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add("/fs/tsk")
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    volumes = list(fd.OpenChildren())
    found = False
    for volume in volumes:
      fd = aff4.FACTORY.Open(volume.urn.Add("Windows/regedit.exe"), mode="r",
                             token=self.token)
      try:
        data = fd.Read(10)
        if data[:2] == "MZ":
          found = True
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

  args = {"pathspec": rdfvalue.RDFPathSpec(
      path="HKEY_LOCAL_MACHINE",
      pathtype=rdfvalue.RDFPathSpec.Enum("REGISTRY"))}
  output_path = "/registry/HKEY_LOCAL_MACHINE"

  def CheckFlow(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    children = list(fd.OpenChildren())
    self.assertTrue("SYSTEM" in [os.path.basename(utils.SmartUnicode(child.urn))
                                 for child in children])

  def TearDown(self):
    urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output_path)
    data_store.DB.DeleteSubject(str(urn.Add("SYSTEM")), token=self.token)
    data_store.DB.DeleteSubject(str(urn), token=self.token)


def RunTests(client_id, platform, testname=None, token=None):
  runner = unittest.TextTestRunner()
  for cls in ClientTestBase.classes.values():
    if testname is not None and testname != cls.__name__:
      continue

    if platform in cls.platforms:
      print "Running %s." % cls.__name__
      runner.run(cls(client_id, token=token))


class TestCPULimit(ClientTestBase):
  platforms = ["linux", "windows", "darwin"]

  flow = "CPULimitTestFlow"

  cpu_limit = 7

  def CheckFlow(self):
    self.assertTrue("CPU quota exceeded." in
                    str(self.session_id.rdf_flow.backtrace))


class CPULimitTestFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  @flow.StateHandler(next_state="State1")
  def Start(self):
    self.CallClient("BusyHang", next_state="State1")

  @flow.StateHandler(next_state="Done")
  def State1(self):
    self.CallClient("BusyHang", next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass
