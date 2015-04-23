#!/usr/bin/env python
"""This modules contains tests for clients API renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import api_test_lib
from grr.gui.api_plugins import client as client_plugin

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class ApiClientsAddLabelsRendererTest(test_lib.GRRBaseTest):
  """Test for ApiClientsAddLabelsRenderer."""

  def setUp(self):
    super(ApiClientsAddLabelsRendererTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.renderer = client_plugin.ApiClientsAddLabelsRenderer()

  def testAddsSingleLabelToSingleClient(self):
    for client_id in self.client_ids:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())

    result = self.renderer.Render(rdfvalue.ApiClientsAddLabelsRendererArgs(
        client_ids=[self.client_ids[0]],
        labels=["foo"]), token=self.token)
    self.assertEqual(result["status"], "OK")

    labels = aff4.FACTORY.Open(self.client_ids[0],
                               token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, self.token.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())

  def testAddsTwoLabelsToTwoClients(self):
    for client_id in self.client_ids:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())

    result = self.renderer.Render(rdfvalue.ApiClientsAddLabelsRendererArgs(
        client_ids=[self.client_ids[0], self.client_ids[1]],
        labels=["foo", "bar"]), token=self.token)
    self.assertEqual(result["status"], "OK")

    for client_id in self.client_ids[:2]:
      labels = aff4.FACTORY.Open(client_id, token=self.token).GetLabels()
      self.assertEqual(len(labels), 2)
      self.assertEqual(labels[0].name, "foo")
      self.assertEqual(labels[0].owner, self.token.username)
      self.assertEqual(labels[1].name, "bar")
      self.assertEqual(labels[1].owner, self.token.username)

    self.assertFalse(
        aff4.FACTORY.Open(self.client_ids[2], token=self.token).GetLabels())


class ApiClientsRemoveLabelsRendererTest(test_lib.GRRBaseTest):
  """Test for ApiClientsRemoveLabelsRenderer."""

  def setUp(self):
    super(ApiClientsRemoveLabelsRendererTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.renderer = client_plugin.ApiClientsRemoveLabelsRenderer()

  def testRemovesUserLabelFromSingleClient(self):
    with aff4.FACTORY.Open(self.client_ids[0], mode="rw",
                           token=self.token) as client:
      client.AddLabels("foo", "bar")

    result = self.renderer.Render(rdfvalue.ApiClientsRemoveLabelsRendererArgs(
        client_ids=[self.client_ids[0]],
        labels=["foo"]), token=self.token)
    self.assertEqual(result["status"], "OK")

    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "bar")
    self.assertEqual(labels[0].owner, self.token.username)

  def testDoesNotRemoveSystemLabelFromSingleClient(self):
    with aff4.FACTORY.Open(self.client_ids[0], mode="rw",
                           token=self.token) as client:
      client.AddLabels("foo", owner="GRR")

    result = self.renderer.Render(rdfvalue.ApiClientsRemoveLabelsRendererArgs(
        client_ids=[self.client_ids[0]],
        labels=["foo"]), token=self.token)
    self.assertEqual(result["status"], "OK")

    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)

  def testRemovesUserLabelWhenSystemLabelWithSimilarNameAlsoExists(self):
    with aff4.FACTORY.Open(self.client_ids[0], mode="rw",
                           token=self.token) as client:
      client.AddLabels("foo")
      client.AddLabels("foo", owner="GRR")

    result = self.renderer.Render(rdfvalue.ApiClientsRemoveLabelsRendererArgs(
        client_ids=[self.client_ids[0]],
        labels=["foo"]), token=self.token)
    self.assertEqual(result["status"], "OK")

    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, "GRR")


class ApiClientSearchRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiClientSearchRenderer"

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_ids = self.SetupClients(1)

      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(client_ids[0], mode="rw",
                             token=self.token) as client:
        client.DeleteAttribute(client.Schema.CERT)

      self.Check("GET", "/api/clients?query=%s" % client_ids[0].Basename())


class ApiClientSummaryRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiClientSummaryRenderer"

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_ids = self.SetupClients(1)

      # Delete the certificats as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(client_ids[0], mode="rw",
                             token=self.token) as client:
        client.DeleteAttribute(client.Schema.CERT)

    self.Check("GET", "/api/clients/%s" % client_ids[0].Basename())


class ApiClientsLabelsListRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiClientsLabelsListRenderer"

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_ids = self.SetupClients(2)

      with aff4.FACTORY.Open(client_ids[0], mode="rw",
                             token=self.token) as client:
        client.AddLabels("foo")

      with aff4.FACTORY.Open(client_ids[1], mode="rw",
                             token=self.token) as client:
        client.AddLabels("bar")

    self.Check("GET", "/api/clients/labels")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
