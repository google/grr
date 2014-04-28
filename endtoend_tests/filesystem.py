#!/usr/bin/env python
"""End to end tests for lib.flows.general.filesystem."""

import re

from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import rdfvalue


####################
# Linux and Darwin #
####################


class TestListDirectoryOSLinuxDarwin(base.ClientTestBase):
  """Tests if ListDirectory works on Linux and Darwin."""
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
      for urn in base.RecursiveListChildren(prefix=base_urn):
        if re.search(self.output_path + "$", str(urn)):
          self.to_delete = urn
          break
      self.assertNotEqual(urn, None, "Could not locate Directory.")
    else:
      urn = self.client_id.Add(self.output_path)

    fd = aff4.FACTORY.Open(urn.Add(self.file_to_find),
                           mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.VFSFile)

  def tearDown(self):
    super(TestListDirectoryOSLinuxDarwin, self).tearDown()
    if hasattr(self, "to_delete"):
      urn = self.to_delete
    else:
      urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(urn.Add(self.file_to_find))
    self.DeleteUrn(urn)
    # Make sure the deletion acutally worked.
    self.assertRaises(AssertionError, self.CheckFlow)


class TestListDirectoryTSKLinuxDarwin(TestListDirectoryOSLinuxDarwin):
  """Tests if ListDirectory works on Linux and Darwin using Sleuthkit."""
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}
  output_path = "/fs/tsk/.*/bin"


class TestRecursiveListDirectoryLinuxDarwin(TestListDirectoryOSLinuxDarwin):
  flow = "RecursiveListDirectory"
  args = {"pathspec": rdfvalue.PathSpec(
      path="/usr",
      pathtype=rdfvalue.PathSpec.PathType.OS),
          "max_depth": 1}
  file_to_find = "less"
  output_path = "/fs/os/usr/bin"


class TestFindTSKLinuxDarwin(TestListDirectoryTSKLinuxDarwin):
  """Tests if the find flow works on Linux and Darwin using Sleuthkit."""
  flow = "FindFiles"

  args = {"findspec": rdfvalue.FindSpec(
      path_regex=".",
      pathspec=rdfvalue.PathSpec(
          path="/bin/",
          pathtype=rdfvalue.PathSpec.PathType.TSK))}


class TestFindOSLinuxDarwin(TestListDirectoryOSLinuxDarwin):
  """Tests if the find flow works on Linux and Darwin."""
  flow = "FindFiles"

  args = {"findspec": rdfvalue.FindSpec(
      path_regex=".",
      pathspec=rdfvalue.PathSpec(
          path="/bin/",
          pathtype=rdfvalue.PathSpec.PathType.OS))}


###########
# Windows #
###########


class TestListDirectoryOSWindows(TestListDirectoryOSLinuxDarwin):
  """Tests if ListDirectory works on Windows."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  file_to_find = "regedit.exe"
  output_path = "/fs/os/C:/Windows"


class TestListDirectoryTSKWindows(TestListDirectoryTSKLinuxDarwin):
  """Tests if ListDirectory works on Windows using Sleuthkit."""
  platforms = ["windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}
  file_to_find = "regedit.exe"

  def CheckFlow(self):
    found = False
    # XP has uppercase...
    for windir in ["Windows", "WINDOWS"]:
      urn = self.client_id.Add("/fs/tsk")
      fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
      volumes = list(fd.OpenChildren())
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



