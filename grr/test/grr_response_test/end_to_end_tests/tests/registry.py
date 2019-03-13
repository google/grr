#!/usr/bin/env python
"""End to end tests for registry-related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import paths as rdf_paths
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

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = "/"
    args.pathspec.pathtype = args.pathspec.REGISTRY

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)
    self.assertIn("/HKEY_LOCAL_MACHINE",
                  [r.payload.pathspec.path for r in results])

  def testListDirectory(self):

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = self.__class__.REG_PATH
    args.pathspec.pathtype = args.pathspec.REGISTRY

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

  def testFindFiles(self):
    args = self.grr_api.types.CreateFlowArgs("FindFiles")
    args.findspec.pathspec.path = self.__class__.REG_PATH
    args.findspec.pathspec.pathtype = args.findspec.pathspec.REGISTRY
    args.findspec.path_regex = "ProfileImagePath"

    f = self.RunFlowAndWait("FindFiles", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    for r in results:
      self.assertIn("ProfileImagePath", r.payload.pathspec.path)

  def testClientFileFinderWithRegistryPath(self):
    base = "/HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/CurrentVersion"
    args = self.grr_api.types.CreateFlowArgs("ClientFileFinder")
    args.paths.append("{}/SystemRo*".format(base))
    args.pathtype = int(rdf_paths.PathSpec.PathType.REGISTRY)
    args.action.action_type = args.action.STAT

    flow = self.RunFlowAndWait("ClientFileFinder", args=args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)
    ff_result = results[0].payload
    stat_entry = ff_result.stat_entry

    self.assertEqual(stat_entry.pathspec.path, "{}/SystemRoot".format(base))
    self.assertEqual(stat_entry.registry_data.string.lower(), r"c:\windows")
    self.assertEqual(stat_entry.st_size, 10)

  def testClientRegistryFinder(self):
    base = "/HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/CurrentVersion"
    args = self.grr_api.types.CreateFlowArgs("ClientRegistryFinder")
    del args.keys_paths[:]  # Clear default paths, which include a sample path.
    args.keys_paths.append("{}/SystemRo*".format(base))

    flow = self.RunFlowAndWait("ClientRegistryFinder", args=args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)
    ff_result = results[0].payload
    stat_entry = ff_result.stat_entry

    self.assertEqual(stat_entry.pathspec.path, "{}/SystemRoot".format(base))
    self.assertEqual(stat_entry.registry_data.string.lower(), r"c:\windows")
    self.assertEqual(stat_entry.st_size, 10)
