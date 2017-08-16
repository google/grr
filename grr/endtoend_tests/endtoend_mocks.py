#!/usr/bin/env python
"""Mocks for end to end testing."""

from grr.endtoend_tests import base
from grr.lib.rdfvalues import paths
from grr.server.flows.general import filesystem
from grr.test_lib import flow_test_lib


class MockEndToEndTest(base.AutomatedTest):
  """Mock test."""
  platforms = ["Linux", "Darwin"]
  flow = filesystem.ListDirectory.__name__
  args = {
      "pathspec":
          paths.PathSpec(path="/bin", pathtype=paths.PathSpec.PathType.OS)
  }

  output_path = "/fs/os/bin"
  file_to_find = "ls"

  def setUp(self):
    pass

  def CheckFlow(self):
    pass

  def tearDown(self):
    pass


class MockEndToEndTestBadFlow(MockEndToEndTest):
  flow = flow_test_lib.RaiseOnStart.__name__
  args = {}


class TestBadSetUp(MockEndToEndTest):

  def setUp(self):
    raise RuntimeError


class TestBadTearDown(MockEndToEndTest):

  def tearDown(self):
    raise RuntimeError


class TestFailure(MockEndToEndTest):

  def CheckFlow(self):
    raise RuntimeError("This should be logged")
