#!/usr/bin/env python
"""End to end tests for registry-related flows."""

from grr_response_test.end_to_end_tests import test_base


class TestFindWindowsRegistry(test_base.EndToEndTest):
  """Test that user listing from the registry works.

  We basically list the registry and then run Find on the same place, we expect
  a single ProfileImagePath value for each user.
  """

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  REG_PATH = ("/HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/"
              "CurrentVersion/ProfileList/")

  def testListHives(self):

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "/"
    args.pathspec.pathtype = args.pathspec.REGISTRY

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    paths = [r.payload.pathspec.path for r in results]
    # TODO(user) - The old agent "fixes" the paths by inserting an extra
    # leading slash and using forward slashes so we unfix them here manually. We
    # can remove this workaround once we no longer test with the old agent.
    paths = [path.removeprefix("/") for path in paths]
    self.assertIn("HKEY_LOCAL_MACHINE", paths)

  def testListDirectory(self):

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = self.__class__.REG_PATH
    args.pathspec.pathtype = args.pathspec.REGISTRY

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

  def testClientRegistryFinder(self):
    base = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
    args = self.grr_api.types.CreateFlowArgs("ClientRegistryFinder")  # pyrefly: ignore[missing-attribute]
    del args.keys_paths[:]  # Clear default paths, which include a sample path.
    args.keys_paths.append("{}\\SystemRo*".format(base))

    flow = self.RunFlowAndWait("ClientRegistryFinder", args=args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)
    ff_result = results[0].payload
    stat_entry = ff_result.stat_entry

    # TODO - The old agent "fixes" the paths by inserting an extra
    # leading slash and using forward slashes so we unfix them here manually. We
    # can remove this workaround once we no longer test with the old agent.
    stat_entry.pathspec.path = stat_entry.pathspec.path.removeprefix("/")
    stat_entry.pathspec.path = stat_entry.pathspec.path.replace("/", "\\")

    self.assertEqual(stat_entry.pathspec.path, "{}\\SystemRoot".format(base))
    self.assertEqual(stat_entry.registry_data.string.lower(), r"c:\windows")
