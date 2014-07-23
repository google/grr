#!/usr/bin/env python
"""End to end tests for lib.flows.general.filesystem."""

import re

from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import rdfvalue


####################
# Linux and Darwin #
####################


class TestListDirectoryOSLinuxDarwin(base.AutomatedTest):
  """Tests if ListDirectory works on Linux and Darwin."""
  platforms = ["Linux", "Darwin"]
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
          self.delete_urns.add(urn.Add(self.file_to_find))
          self.delete_urns.add(urn)
          break
      self.assertNotEqual(urn, None, "Could not locate Directory.")
    else:
      urn = self.client_id.Add(self.output_path)

    fd = aff4.FACTORY.Open(urn.Add(self.file_to_find),
                           mode="r", token=self.token)
    if type(fd) == aff4.AFF4Volume:
      self.fail(("No results were written to the data store. Maybe the GRR "
                 "client is not running with root privileges?"))
    self.assertEqual(type(fd), aff4.VFSFile)

  def tearDown(self):
    if not self.delete_urns:
      self.delete_urns.add(
          self.client_id.Add(self.output_path).Add(self.file_to_find))
    super(TestListDirectoryOSLinuxDarwin, self).tearDown()


# TODO(user): Find a way to run this on Darwin with Filevault turned on.
class TestListDirectoryTSKLinux(TestListDirectoryOSLinuxDarwin):
  """Tests if ListDirectory works on Linux and Darwin using Sleuthkit."""
  platforms = ["Linux"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin",
      pathtype=rdfvalue.PathSpec.PathType.TSK)}
  output_path = "/fs/tsk/.*/bin"


class TestRecursiveListDirectoryLinuxDarwin(TestListDirectoryOSLinuxDarwin):
  """Test recursive list directory on linux and darwin."""
  flow = "RecursiveListDirectory"
  file_to_find = "less"
  output_path = "/fs/os/usr/bin"
  args = {"pathspec": rdfvalue.PathSpec(
      path="/usr", pathtype=rdfvalue.PathSpec.PathType.OS),
          "max_depth": 1}


# TODO(user): Find a way to run this on Darwin with Filevault turned on.
class TestFindTSKLinux(TestListDirectoryTSKLinux):
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
  platforms = ["Windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  file_to_find = "regedit.exe"
  output_path = "/fs/os/C:/Windows"


class TestListDirectoryTSKWindows(TestListDirectoryTSKLinux):
  """Tests if ListDirectory works on Windows using Sleuthkit."""
  platforms = ["Windows"]
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
            self.delete_urns.add(child.urn.Add(self.file_to_find))
            self.delete_urns.add(child.urn)
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
