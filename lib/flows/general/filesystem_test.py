#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the filesystem related flows."""

import os

from grr.client import vfs
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class TestFilesystem(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def testListDirectoryOfTSKFile(self):
    """Test that the TSK VFS containers are opened automatically."""
    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

    # Deliberately specify incorrect casing for the image name.
    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(pb.first.path)

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 6)

    # Check that the object is stored with the correct casing.
    self.assertTrue("lost+found" in [x.urn.Basename() for x in children])

    # And the wrong object is not there
    self.assertRaises(IOError, aff4.FACTORY.Open,
                      output_path.Add("test directory"),
                      aff4_type="VFSDirectory", token=self.token)

  def testListDirectory(self):
    """Test that the ListDirectory flow works."""
    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

    # Deliberately specify incorrect casing for the image name.
    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd/test directory"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(
        os.path.dirname(pb.first.path))

    fd = aff4.FACTORY.Open(output_path.Add("Test Directory"), token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]

    # Check that the object is stored with the correct casing.
    self.assertEqual(child.urn.Basename(), "numbers.txt")

    # And the wrong object is not there
    self.assertRaises(IOError, aff4.FACTORY.Open,
                      output_path.Add("test directory"),
                      aff4_type="VFSDirectory", token=self.token)

  def testUnicodeListDirectory(self):
    """Test that the ListDirectory flow works on unicode directories."""

    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

    # Deliberately specify incorrect casing
    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    pb.Append(path=u"入乡随俗 海外春节别样过法",
              pathtype=rdfvalue.PathSpec.PathType.TSK)

    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(pb.CollapsePath())

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    self.assertEqual(
        os.path.basename(utils.SmartUnicode(child.urn)), u"入乡随俗.txt")

  def testSlowGetFile(self):
    """Test that the SlowGetFile flow works."""
    client_mock = test_lib.ActionMock("ReadBuffer", "HashFile", "StatFile")

    # Deliberately specify incorrect casing
    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    pb.Append(path="test directory/NumBers.txt",
              pathtype=rdfvalue.PathSpec.PathType.TSK)

    for _ in test_lib.TestFlowHelper(
        "SlowGetFile", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(
        pb.first.path.replace("\\", "/")).Add(
            "Test Directory").Add("numbers.txt")

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertEqual(fd.Read(10), "1\n2\n3\n4\n5\n")
    self.assertEqual(fd.size, 3893)

    # And the wrong object is not there
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertRaises(IOError, client.OpenMember, pb.first.path)

    # Check that the hash is recorded correctly.
    sha256 = fd.Get(fd.Schema.HASH).sha256
    self.assertEqual(
        sha256,
        "67d4ff71d43921d5739f387da09746f405e425b07d727e4c69d029461d1f051f")

  def testGlob(self):
    """Test that glob works properly."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = client.Schema.USER()
    users.Append(username="test")
    users.Append(username="syslog")
    client.Set(users)
    client.Close()

    client_mock = test_lib.ActionMock("Find", "StatFile")

    # This glob selects all files which start with the username on this system.
    paths = [os.path.join(self.base_path, "%%Users.username%%*"),
             os.path.join(self.base_path, "wtmp")]

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/os").Add(
        self.base_path.replace("\\", "/"))

    children = []
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    for child in fd.ListChildren():
      children.append(child.Basename())

    # We should find some files.
    self.assertEqual(sorted(children),
                     sorted(["syslog", "syslog_compress.gz",
                             "syslog_false.gz", "test_img.dd", "test.plist",
                             "tests", "tests_long", "wtmp"]))

  def testGlobWithStarStar(self):
    """Test that ** expressions mean recursion."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = client.Schema.USER()
    users.Append(username="test")
    users.Append(username="syslog")
    client.Set(users)
    client.Close()

    client_mock = test_lib.ActionMock("Find", "StatFile")

    # Glob for foo at a depth of 4.
    paths = [
        os.path.join(self.base_path, "test_img.dd/", "foo**4")]

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(
        self.base_path.replace("\\", "/")).Add("test_img.dd/glob_test/a/b")

    children = []
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    for child in fd.ListChildren():
      children.append(child.Basename())

    # We should find some files.
    self.assertEqual(children, ["foo"])

  def testGlobWithInvalidStarStar(self):
    client_mock = test_lib.ActionMock("Find", "StatFile")

    # This glob is invalid since it uses 2 ** expressions..
    paths = [os.path.join(self.base_path, "test_img.dd", "**", "**", "foo")]

    # Make sure the flow raises.
    self.assertRaises(ValueError, list, test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token))

  def testGlobWithWildcardsInsideTSKFile(self):
    client_mock = test_lib.ActionMock("Find", "StatFile")

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join(self.base_path, "test_img.dd", "*", "a", "b", "*")

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(os.path.join(
        self.base_path, "test_img.dd", "glob_test", "a", "b"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.ListChildren())

    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].Basename(), "foo")

  def testGlobWithWildcardInTSKFilename(self):
    client_mock = test_lib.ActionMock("Find", "StatFile")

    # This glob should find this file in test data: glob_test/a/b/foo. Match the
    # file with the wrong case to test case insensitive globbing.
    path = os.path.join(self.base_path, "test_IMG.*", "*", "a", "b", "*")

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(os.path.join(
        self.base_path, "test_img.dd", "glob_test", "a", "b"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.ListChildren())

    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].Basename(), "foo")

  def testGlobDirectory(self):
    """Test that glob expands directories."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    user_attribute = client.Schema.USER()

    user_record = rdfvalue.User()
    user_record.special_folders.app_data = "test_data/index.dat"
    user_attribute.Append(user_record)

    user_record = rdfvalue.User()
    user_record.special_folders.app_data = "test_data/History"
    user_attribute.Append(user_record)

    # This is a record which means something to the interpolation system. We
    # should not process this especially.
    user_record = rdfvalue.User()
    user_record.special_folders.app_data = "%%PATH%%"
    user_attribute.Append(user_record)

    client.Set(user_attribute)

    client.Close()

    client_mock = test_lib.ActionMock("Find", "StatFile")

    # This glob selects all files which start with the username on this system.
    path = os.path.join(os.path.dirname(self.base_path),
                        "%%Users.special_folders.app_data%%")

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

    path = self.client_id.Add("fs/os").Add(self.base_path).Add("index.dat")

    aff4.FACTORY.Open(path, aff4_type="VFSFile", token=self.token)

    path = self.client_id.Add("fs/os").Add(self.base_path).Add("index.dat")

    aff4.FACTORY.Open(path, aff4_type="VFSFile", token=self.token)

  def testGlobGrouping(self):
    """Test that glob expands directories."""

    pattern = "test_data/{ntfs_img.dd,*.log,*.raw}"

    client_mock = test_lib.ActionMock("Find", "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

  def testIllegalGlob(self):
    """Test that illegal globs raise."""

    paths = ["Test/%%Weird_illegal_attribute%%"]

    # Run the flow - we expect an AttributeError error to be raised from the
    # flow since Weird_illegal_attribute is not a valid client attribute.
    self.assertRaises(AttributeError, flow.GRRFlow.StartFlow,
                      flow_name="Glob", paths=paths,
                      client_id=self.client_id, token=self.token)

  def testIllegalGlobAsync(self):
    # When running the flow asynchronously, we will not receive any errors from
    # the Start method, but the flow should still fail.
    paths = ["Test/%%Weird_illegal_attribute%%"]
    client_mock = test_lib.ActionMock("Find", "StatFile")

    # Run the flow.
    session_id = None

    # This should not raise here since the flow is run asynchronously.
    for session_id in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id, check_flow_errors=False,
        paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS, token=self.token,
        sync=False):
      pass

    fd = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertTrue("AttributeError" in fd.state.context.backtrace)
    self.assertEqual("ERROR", str(fd.state.context.state))

  def testFetchFilesFlow(self):

    pattern = "test_data/*.log"

    client_mock = test_lib.ActionMock("Find", "TransferBuffer",
                                      "StatFile", "HashBuffer", "HashFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "FetchFiles", client_mock, client_id=self.client_id,
        paths=[path], pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    for f in "auth.log dpkg.log dpkg_false.log".split():
      fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(
          os.path.join(os.path.dirname(self.base_path), "test_data", f)),
                             token=self.token)
      # Make sure that some data was downloaded.
      self.assertTrue(fd.Get(fd.Schema.SIZE) > 100)

  def testDownloadDirectory(self):
    """Test a FetchFiles flow with depth=1."""
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture

    # Mock the client actions FetchFiles uses
    client_mock = test_lib.ActionMock("HashFile", "HashBuffer", "StatFile",
                                      "Find", "TransferBuffer")

    pathspec = rdfvalue.PathSpec(
        path="/c/Downloads", pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in test_lib.TestFlowHelper(
        "FetchFiles", client_mock, client_id=self.client_id,
        findspec=rdfvalue.FindSpec(max_depth=1, pathspec=pathspec,
                                   path_glob="*"),
        token=self.token):
      pass

    # Check if the base path was created
    output_path = self.client_id.Add("fs/os/c/Downloads")

    output_fd = aff4.FACTORY.Open(output_path, token=self.token)

    children = list(output_fd.OpenChildren())

    # There should be 5 children: a.txt, b.txt, c.txt, d.txt sub1
    self.assertEqual(len(children), 5)

    self.assertEqual("a.txt b.txt c.txt d.txt sub1".split(),
                     sorted([child.urn.Basename() for child in children]))

    # Find the child named: a.txt
    for child in children:
      if child.urn.Basename() == "a.txt":
        break

    # Check the AFF4 type of the child, it should have changed
    # from VFSFile to VFSBlobImage
    self.assertEqual(child.__class__.__name__, "VFSBlobImage")

  def testDownloadDirectorySub(self):
    """Test a FetchFiles flow with depth=5."""
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture

    # Mock the client actions FetchFiles uses
    client_mock = test_lib.ActionMock("HashFile", "HashBuffer", "StatFile",
                                      "Find", "TransferBuffer")

    pathspec = rdfvalue.PathSpec(
        path="/c/Downloads", pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in test_lib.TestFlowHelper(
        "FetchFiles", client_mock, client_id=self.client_id,
        findspec=rdfvalue.FindSpec(max_depth=5, pathspec=pathspec,
                                   path_glob="*"),
        token=self.token):
      pass

    # Check if the base path was created
    output_path = self.client_id.Add("fs/os/c/Downloads")

    output_fd = aff4.FACTORY.Open(output_path, token=self.token)

    children = list(output_fd.OpenChildren())

    # There should be 5 children: a.txt, b.txt, c.txt, d.txt, sub1
    self.assertEqual(len(children), 5)

    self.assertEqual("a.txt b.txt c.txt d.txt sub1".split(),
                     sorted([child.urn.Basename() for child in children]))

    # Find the child named: sub1
    for child in children:
      if child.urn.Basename() == "sub1":
        break

    children = list(child.OpenChildren())

    # There should be 4 children: a.txt, b.txt, c.txt, d.txt
    self.assertEqual(len(children), 4)

    self.assertEqual("a.txt b.txt c.txt d.txt".split(),
                     sorted([child.urn.Basename() for child in children]))
