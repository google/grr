#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for components.

This test can be used to ensure that a component is self contained by replacing
the component in grr/test_data/ with the real component.
"""
import inspect
import os

from grr.client import comms
from grr.client.components.rekall_support import grr_rekall
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client


class MockHTTPManager(object):

  def __init__(self, token):
    self.token = token

  def OpenServerEndpoint(self, url):
    fd = aff4.FACTORY.Open("aff4:/web" + url, token=self.token)
    return comms.HTTPObject(data=fd.read(100e6), code=200)


class MockClientWorker(object):
  """Mock client worker."""

  def __init__(self, token):
    self.http_manager = MockHTTPManager(token)


class TestComponents(test_lib.EmptyActionTest):

  def setUp(self):
    super(TestComponents, self).setUp()
    self.component = test_lib.WriteComponent(token=self.token)

    # The Rekall component will bring in all these new objects. Since the rekall
    # component code is already loaded when the component is re-imported, Rekall
    # will complain about duplicate definitions. We cheat by clearing the Rekall
    # registry first.

    # Note that the new component should re-register its own handlers for these
    # objects which is how we verify the component has been properly installed.
    grr_rekall.GRRObjectRenderer.classes.clear()
    grr_rekall.RekallCachingIOManager.classes.clear()
    grr_rekall.GrrRekallSession.classes.clear()
    grr_rekall.GRRRekallRenderer.classes.clear()

  def testComponentLoading(self):
    """Ensure we can load the component."""
    message = rdf_client.LoadComponent(
        summary=self.component.summary)

    # The client uses its build_environment configuration to call the correct
    # version of the component. It is normally populated by the build system but
    # in this test we set it to a known value.
    with test_lib.ConfigOverrider({
        "Client.build_environment": "Linux_Ubuntu_glibc_2.4_amd64",
        "Client.component_path": os.path.join(self.temp_dir, "components")}):
      self.RunAction("LoadComponent", message,
                     grr_worker=MockClientWorker(self.token))

      # We get the path where the client action is actually loaded from.
      client_action_path = inspect.getsourcefile(
          grr_rekall.GRRObjectRenderer.classes["GRRObjectRenderer"])

      # Now we need to make sure this is coming from the component, rather than
      # the source tree.
      self.assertTrue(config_lib.CONFIG["Client.component_path"] in
                      client_action_path)
      self.assertTrue("grr-rekall/0.1/" in client_action_path)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
