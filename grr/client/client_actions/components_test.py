#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for components.

This test can be used to ensure that a component is self contained by replacing
the component in grr/test_data/ with the real component.
"""
import os
import StringIO
import zipfile

from grr.client import comms
from grr.lib import aff4
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
  """Test the ability to load arbitrary components."""

  # This component will leave its mark on the os module when imported.
  component_payload = """
import os
os._grr_component_was_here = True
"""

  def setUp(self):
    super(TestComponents, self).setUp()

    # Create a mock component.
    fp = StringIO.StringIO()
    new_zip_file = zipfile.ZipFile(fp, mode="w")
    new_zip_file.writestr("mock_mod.py", self.component_payload)
    new_zip_file.close()

    self.component = test_lib.WriteComponent(name="mock_component",
                                             version="1.0",
                                             token=self.token,
                                             modules=["mock_mod"],
                                             raw_data=fp.getvalue())

  def testComponentLoading(self):
    """Ensure we can load the component."""
    message = rdf_client.LoadComponent(summary=self.component.summary)

    # The client uses its build_environment configuration to call the correct
    # version of the component. It is normally populated by the build system but
    # in this test we set it to a known value which is the same as we created
    # earlier.
    with test_lib.ConfigOverrider({
        "Client.build_environment": self.component.build_system.signature(),
        "Client.component_path": os.path.join(self.temp_dir, "components")
    }):
      self.RunAction("LoadComponent",
                     message,
                     grr_worker=MockClientWorker(self.token))

      # Make sure that the component was loaded.
      self.assertTrue(getattr(os, "_grr_component_was_here", False))


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
