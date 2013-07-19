#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the filesystem related flows."""

import os

from grr.lib import aff4
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
    self.assertEqual(
        str(fd.Get(fd.Schema.HASH)),
        "67d4ff71d43921d5739f387da09746f405e425b07d727e4c69d029461d1f051f")

  def testGlob(self):
    """Test that glob works properly."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.USERNAMES("test syslog"))
    client.Close()

    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

    # This glob selects all files which start with the username on this system.
    path = os.path.join(self.base_path, "%%Usernames%%*")

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/os").Add(
        self.base_path.replace("\\", "/"))

    count = 0
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    for child in fd.ListChildren():
      childname = child.Basename()
      self.assertTrue(childname.startswith("test") or
                      childname.startswith("syslog"))
      count += 1

    # We should find some files.
    self.assertTrue(count >= 6)

  def testGlobWithWildcardsInsideTSKFile(self):
    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

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
    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join(self.base_path, "test_img.*", "*", "a", "b", "*")

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

    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")

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

    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

  def testIllegalGlob(self):
    """Test that illegal globs raise."""

    pattern = "Test/%%Weird_illegal_attribute%%"

    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow - we expect an AttributeError error to be raised from the
    # flow since Weird_illegal_attribute is not a valid client attribute.
    self.assertRaises(AttributeError, list, test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], token=self.token))

  def testGlobAndDownload(self):

    pattern = "test_data/*.log"

    client_mock = test_lib.ActionMock("ListDirectory", "TransferBuffer",
                                      "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "GlobAndDownload", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

    for f in "auth.log dpkg.log dpkg_false.log".split():
      fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(
          os.path.join(os.path.dirname(self.base_path), "test_data", f)),
                             token=self.token)
      # Make sure that some data was downloaded.
      self.assertTrue(fd.Get(fd.Schema.SIZE) > 100)

  def BrokenTestGlobAndGrep(self):
    """Disabled test.

    TODO(user): this test doesn't work because globandrunflow runs
    multiple greps that all trash each others output collections.
    """
    pattern = "test_data/*.log"

    client_mock = test_lib.ActionMock("ListDirectory", "Grep", "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    args = {"request": rdfvalue.GrepSpec(
        target=rdfvalue.PathSpec(),
        literal="session opened for user dearjohn",
        mode=rdfvalue.GrepSpec.Mode.ALL_HITS
        ),
            "output": "analysis/grep/testing"}

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "GlobAndGrep", client_mock, client_id=self.client_id,
        paths=[path], token=self.token, **args):
      pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("/analysis/grep/testing"),
        token=self.token)
    # Make sure that there is a hit.
    # TODO(user): multiple runs of this test sometimes return 0 results.
    self.assertEqual(len(fd), 1)
    first = fd[0]
    self.assertEqual(first.offset, 350)
    self.assertEqual(first.data,
                     "session): session opened for user dearjohn by (uid=0")

  def testGlobAndListDirectory(self):

    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(
        os.path.join(os.path.dirname(self.base_path), "test_data")),
                           token=self.token)
    self.assertEqual(len(list(fd.ListChildren())), 0)

    pattern = "test_*"

    client_mock = test_lib.ActionMock("ListDirectory", "TransferBuffer",
                                      "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "GlobAndListDirectory", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(
        os.path.join(os.path.dirname(self.base_path), "test_data")),
                           token=self.token)

    children = list(fd.ListChildren())
    self.assertGreater(len(children), 30)
    filenames = [os.path.basename(str(f)) for f in children]

    for f in "auth.log dpkg.log dpkg_false.log".split():
      self.assertIn(f, filenames)
