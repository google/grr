#!/usr/bin/env python
"""End to end tests for registry-related flows."""
from __future__ import absolute_import
from __future__ import division

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
    self.assertGreater(len(results), 0)
    self.assertIn("/HKEY_LOCAL_MACHINE",
                  [r.payload.pathspec.path for r in results])

  def testListDirectory(self):

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = self.__class__.REG_PATH
    args.pathspec.pathtype = args.pathspec.REGISTRY

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertGreater(len(results), 0)

  def testFindFiles(self):
    args = self.grr_api.types.CreateFlowArgs("FindFiles")
    args.findspec.pathspec.path = self.__class__.REG_PATH
    args.findspec.pathspec.pathtype = args.findspec.pathspec.REGISTRY
    args.findspec.path_regex = "ProfileImagePath"

    f = self.RunFlowAndWait("FindFiles", args=args)

    results = list(f.ListResults())
    self.assertGreater(len(results), 0)

    for r in results:
      self.assertIn("ProfileImagePath", r.payload.pathspec.path)
