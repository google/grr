#!/usr/bin/env python
"""End to end tests for lib.flows.general.filesystem."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.aff4_objects import standard
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths

####################
# Linux and Darwin #
####################


class TestListDirectoryOSLinuxDarwin(base.TestVFSPathExists):
  """Tests if ListDirectory works on Linux and Darwin."""
  platforms = ["Linux", "Darwin"]
  flow = "ListDirectory"
  args = {"pathspec": rdf_paths.PathSpec(
      path="/bin", pathtype=rdf_paths.PathSpec.PathType.OS)}
  output_path = "/fs/os/bin"
  file_to_find = "ls"


# TODO(user): Find a way to run this on Darwin with Filevault turned on.
class TestListDirectoryTSKLinux(base.TestVFSPathExists):
  """Tests if ListDirectory works on Linux and Darwin using Sleuthkit."""
  # We look for the bin directory inside /usr. It's very difficult to find a
  # file common across all versions of default OS X, Ubuntu, and CentOS that
  # isn't symlinked and doesn't live in a huge directory that takes forever to
  # list with TSK. So we settle for a directory instead.
  platforms = ["Linux"]
  flow = "ListDirectory"
  args = {"pathspec": rdf_paths.PathSpec(
      path="/usr", pathtype=rdf_paths.PathSpec.PathType.TSK)}
  output_path = "/fs/tsk/.*/usr"
  result_type = standard.VFSDirectory
  file_to_find = "bin"


class TestRecursiveListDirectoryLinuxDarwin(base.TestVFSPathExists):
  """Test recursive list directory on linux and darwin."""
  platforms = ["Linux", "Darwin"]
  flow = "RecursiveListDirectory"
  args = {"pathspec": rdf_paths.PathSpec(
      path="/usr", pathtype=rdf_paths.PathSpec.PathType.OS),
          "max_depth": 1}
  output_path = "/fs/os/usr/bin"
  file_to_find = "less"


# TODO(user): Find a way to run this on Darwin with Filevault turned on.
class TestFindTSKLinux(base.TestVFSPathExists):
  """Tests if the find flow works on Linux and Darwin using Sleuthkit."""
  platforms = ["Linux"]
  flow = "FindFiles"
  args = {"findspec": rdf_client.FindSpec(
      # Cut down the number of files by specifying a partial regex match, we
      # just want to find /usr/bin/diff, when run on a real system there are
      # thousands which takes forever with TSK.
      path_regex="di",
      pathspec=rdf_paths.PathSpec(
          path="/usr/bin/", pathtype=rdf_paths.PathSpec.PathType.TSK))}
  output_path = "/fs/tsk/.*/usr/bin"
  file_to_find = "diff"


class TestFindOSLinuxDarwin(base.TestVFSPathExists):
  """Tests if the find flow works on Linux and Darwin."""
  platforms = ["Linux", "Darwin"]
  flow = "FindFiles"
  args = {"findspec": rdf_client.FindSpec(
      path_regex=".",
      pathspec=rdf_paths.PathSpec(
          path="/bin/", pathtype=rdf_paths.PathSpec.PathType.OS))}
  output_path = "/fs/os/bin"
  file_to_find = "ls"

###########
# Windows #
###########


class TestListDirectoryOSWindows(base.TestVFSPathExists):
  """Tests if ListDirectory works on Windows."""
  platforms = ["Windows"]
  flow = "ListDirectory"
  args = {"pathspec": rdf_paths.PathSpec(
      path="C:\\Windows", pathtype=rdf_paths.PathSpec.PathType.OS)}
  output_path = "/fs/os/C:/Windows"
  file_to_find = "regedit.exe"


class TestListDirectoryTSKWindows(base.TestVFSPathExists):
  """Tests if ListDirectory works on Windows using Sleuthkit."""
  platforms = ["Windows"]
  flow = "ListDirectory"
  args = {"pathspec": rdf_paths.PathSpec(
      path="C:\\Windows", pathtype=rdf_paths.PathSpec.PathType.TSK)}
  output_path = "/fs/tsk/.*/C:/Windows"
  file_to_find = "regedit.exe"

  def CheckFlow(self):
    found = False
    # XP has uppercase...
    for windir in ["Windows", "WINDOWS"]:
      urn = self.client_id.Add("/fs/tsk")
      fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
      volumes = list(fd.OpenChildren())
      for volume in volumes:
        fd = aff4.FACTORY.Open(
            volume.urn.Add(windir), mode="r", token=self.token)
        children = list(fd.OpenChildren())
        for child in children:
          if self.file_to_find == child.urn.Basename():
            # We found what we were looking for.
            found = True
            self.delete_urns.add(child.urn.Add(self.file_to_find))
            self.delete_urns.add(child.urn)
            break
    self.assertTrue(found)


class TestRecursiveListDirectoryOSWindows(base.TestVFSPathExists):
  platforms = ["Windows"]
  flow = "RecursiveListDirectory"
  args = {"pathspec": rdf_paths.PathSpec(
      path="C:\\", pathtype=rdf_paths.PathSpec.PathType.OS),
          "max_depth": 1}
  output_path = "/fs/os/C:/Windows"
  file_to_find = "regedit.exe"
