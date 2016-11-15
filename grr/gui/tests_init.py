#!/usr/bin/env python
"""Init methods for setting up GUI tests."""


from grr.lib import access_control
from grr.lib import aff4
from grr.lib import client_index
from grr.lib import data_store
from grr.lib import registry
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.rdfvalues import client as rdf_client


class RunTestsInit(registry.InitHook):
  """Init hook that sets up test fixtures."""

  pre = ["AFF4InitHook"]

  # We cache all the AFF4 objects created by this fixture so its faster to
  # recreate it between tests.
  fixture_cache = None

  def Run(self):
    """Run the hook setting up fixture and security mananger."""
    # Install the mock security manager so we can trap errors in interactive
    # mode.
    data_store.DB.security_manager = test_lib.MockSecurityManager()
    self.token = access_control.ACLToken(
        username="test", reason="Make fixtures.")
    self.token = self.token.SetUID()

    self.BuildFixture()

  def BuildFixture(self):
    for i in range(10):
      client_id = rdf_client.ClientURN("C.%016X" % i)
      with aff4.FACTORY.Create(
          client_id, aff4_grr.VFSGRRClient, mode="rw",
          token=self.token) as client_obj:
        index = client_index.CreateClientIndex(token=self.token)
        index.AddClient(client_obj)


class TestPluginInit(registry.InitHook):
  """Load the test plugins after django is initialized."""
  pre = ["DjangoInit"]

  def RunOnce(self):
    # pylint: disable=unused-variable,g-import-not-at-top
    from grr.gui.plugins import tests
    # pylint: enable=unused-variable,g-import-not-at-top
