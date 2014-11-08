#!/usr/bin/env python
"""Test the filesystem related flows."""

import os

from grr.client import client_utils_linux
from grr.client import client_utils_osx
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestChromePlugins(test_lib.FlowTestsBaseclass):
  """Test the chrome extension flow."""

  def testGetExtension(self):
    """Test that finding the Chrome plugin works."""

    # Set up client info
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw",
                                    token=self.token)

    self.client.Set(self.client.Schema.SYSTEM("Linux"))

    user_list = self.client.Schema.USER()

    for u in [rdfvalue.User(username="Foo",
                            full_name="FooFoo",
                            last_logon=150),
              rdfvalue.User(username="test",
                            full_name="test user",
                            homedir="/home/test/",
                            last_logon=250)]:
      user_list.Append(u)

    self.client.AddAttribute(self.client.Schema.USER, user_list)

    self.client.Close()

    client_mock = action_mocks.ActionMock(
        "ReadBuffer", "FingerprintFile", "TransferBuffer", "StatFile",
        "ListDirectory", "HashBuffer", "Find")

    # TODO(user): Find a way to do this on Windows.
    # Mock the client to make it look like the root partition is mounted off the
    # test image. This will force all flow access to come off the image.
    def MockGetMountpoints():
      return {
          "/": (os.path.join(self.base_path, "test_img.dd"), "ext2")
          }
    orig_linux_mp = client_utils_linux.GetMountpoints
    orig_osx_mp = client_utils_osx.GetMountpoints
    client_utils_linux.GetMountpoints = MockGetMountpoints
    client_utils_osx.GetMountpoints = MockGetMountpoints
    try:
      # Run the flow in the simulated way
      for _ in test_lib.TestFlowHelper(
          "ChromePlugins", client_mock, client_id=self.client_id,
          username="test", download_files=True, output="analysis/plugins",
          token=self.token, pathtype=rdfvalue.PathSpec.PathType.TSK):
        pass

      # Now check that the right files were downloaded.
      fs_path = ("/home/test/.config/google-chrome/Default/Extensions/"
                 "nlbjncdgjeocebhnmkbbbdekmmmcbfjd/2.1.3_0")

      # Check if the output VFile is created
      output_path = self.client_id.Add("fs/tsk").Add(
          "/".join([self.base_path.replace("\\", "/"),
                    "test_img.dd"])).Add(fs_path)

      fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(fd.OpenChildren())
      self.assertEqual(len(children), 3)

      # Check for Analysis dir
      output_path = self.client_id.Add(
          "analysis/plugins/RSS Subscription Extension (by Google)/2.1.3")

      fd = aff4.FACTORY.Open(output_path, token=self.token)
      self.assertEqual(fd.Get(fd.Schema.NAME),
                       "RSS Subscription Extension (by Google)")
      self.assertEqual(fd.Get(fd.Schema.VERSION),
                       "2.1.3")
      self.assertEqual(fd.Get(fd.Schema.CHROMEID),
                       "nlbjncdgjeocebhnmkbbbdekmmmcbfjd")
      self.assertEqual(fd.Get(fd.Schema.EXTENSIONDIR),
                       fs_path)

      # check for file downloads
      urns = [str(c.urn) for c in children
              if str(c.urn).endswith("testfile.txt")]
      self.assertEqual(len(urns), 1)

      fd = aff4.FACTORY.Open(urns[0], token=self.token)
      expect = "This should be downloaded automatically."
      self.assertTrue(fd.Read(10000).startswith(expect))
      self.assertEqual(fd.size, 41)

    finally:
      client_utils_linux.GetMountpoints = orig_linux_mp
      client_utils_osx.GetMountpoints = orig_osx_mp


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = TestChromePlugins


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
