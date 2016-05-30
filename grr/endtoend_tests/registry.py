#!/usr/bin/env python
"""End to end tests for lib.flows.general.registry."""

import os

from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow_utils
from grr.lib import utils
from grr.lib.flows.console import debugging
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class TestFindWindowsRegistry(base.ClientTestBase):
  """Test that user listing from the registry works.

  We basically list the registry and then run Find on the same place, we expect
  a single ProfileImagePath value for each user.

  TODO(user): this is excluded from automated tests for now because it needs
  to run two flows and defines its own runTest to do so.  We should support
  this but it requires more work.
  """
  platforms = ["Windows"]
  reg_path = ("/HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/"
              "CurrentVersion/ProfileList/")

  output_path = "analysis/find/test"

  def runTest(self):
    """Launch our flows."""
    for flow, args in [
        ("ListDirectory", {"pathspec": rdf_paths.PathSpec(
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
            path=self.reg_path)}),
        ("FindFiles",
         {"findspec": rdf_client.FindSpec(pathspec=rdf_paths.PathSpec(
             path=self.reg_path,
             pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
                                          path_regex="ProfileImagePath"),
          "output": self.output_path})
    ]:

      if self.local_worker:
        self.session_id = debugging.StartFlowAndWorker(self.client_id, flow,
                                                       **args)
      else:
        self.session_id = flow_utils.StartFlowAndWait(self.client_id,
                                                      flow_name=flow,
                                                      token=self.token,
                                                      **args)

    self.CheckFlow()

  def CheckFlow(self):
    """Check that all profiles listed have an ProfileImagePath."""
    urn = self.client_id.Add("registry").Add(self.reg_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)

    user_accounts = sorted([x.urn for x in fd.OpenChildren()
                            if x.urn.Basename().startswith("S-")])

    urn = self.client_id.Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    hits = sorted([x.aff4path for x in fd])

    self.assertGreater(len(hits), 1)
    self.assertEqual(len(hits), len(user_accounts))

    for x, y in zip(user_accounts, hits):
      self.assertEqual(x.Add("ProfileImagePath"), y)


class TestClientRegistry(base.AutomatedTest):
  """Tests if listing registry keys works on Windows."""
  platforms = ["Windows"]
  flow = "ListDirectory"

  args = {"pathspec": rdf_paths.PathSpec(
      path="HKEY_LOCAL_MACHINE",
      pathtype=rdf_paths.PathSpec.PathType.REGISTRY)}
  output_path = "/registry/HKEY_LOCAL_MACHINE"

  def CheckFlow(self):
    urn = self.client_id.Add(self.output_path)
    fd = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    children = list(fd.OpenChildren())
    self.assertTrue("SYSTEM" in [os.path.basename(utils.SmartUnicode(child.urn))
                                 for child in children])

  def tearDown(self):
    urn = self.client_id.Add(self.output_path)
    data_store.DB.DeleteSubject(str(urn.Add("SYSTEM")), token=self.token)
    data_store.DB.DeleteSubject(str(urn), token=self.token)
