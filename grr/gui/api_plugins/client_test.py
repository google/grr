#!/usr/bin/env python
"""This modules contains tests for clients API handlers."""


from grr.gui import api_test_lib
from grr.gui.api_plugins import client as client_plugin

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import test_base as rdf_test_base
from grr.server import aff4
from grr.server import client_index
from grr.server import data_store
from grr.server import events
from grr.server.flows.general import audit

from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class ApiClientIdTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test for ApiClientId."""

  rdfvalue_class = client_plugin.ApiClientId

  def GenerateSample(self, number=0):
    return client_plugin.ApiClientId("C.%016d" % number)

  def testRaisesWhenInitializedFromInvalidValues(self):
    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("blah")

    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("C.0")

    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("C." + "0" * 15)

    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("C." + "1" * 16 + "/foo")

  def testRaisesWhenToClientURNCalledOnUninitializedValue(self):
    client_id = client_plugin.ApiClientId()
    with self.assertRaises(ValueError):
      client_id.ToClientURN()

  def testConvertsToClientURN(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    client_urn = client_id.ToClientURN()

    self.assertEqual(client_urn.Basename(), client_id)
    self.assertEqual(client_urn, "aff4:/C." + "1" * 16)


class ApiAddClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiAddClientsLabelsHandler."""

  def setUp(self):
    super(ApiAddClientsLabelsHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiAddClientsLabelsHandler()

  def testAddsSingleLabelToSingleClient(self):
    for client_id in self.client_ids:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())
      data_store.REL_DB.WriteClientMetadata(
          client_id.Basename(), fleetspeak_enabled=False)

    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, self.token.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())

    # Relational DB labels.
    cid = self.client_ids[0].Basename()
    labels = data_store.REL_DB.GetClientLabels(cid)
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, self.token.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(data_store.REL_DB.GetClientLabels(client_id.Basename()))

  def testAddsTwoLabelsToTwoClients(self):
    for client_id in self.client_ids:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())
      data_store.REL_DB.WriteClientMetadata(
          client_id.Basename(), fleetspeak_enabled=False)

    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0], self.client_ids[1]],
            labels=["foo", "bar"]),
        token=self.token)

    # AFF4 labels.
    for client_id in self.client_ids[:2]:
      labels = aff4.FACTORY.Open(client_id, token=self.token).GetLabels()
      self.assertEqual(len(labels), 2)
      self.assertEqual(labels[0].name, "foo")
      self.assertEqual(labels[0].owner, self.token.username)
      self.assertEqual(labels[1].name, "bar")
      self.assertEqual(labels[1].owner, self.token.username)

    self.assertFalse(
        aff4.FACTORY.Open(self.client_ids[2], token=self.token).GetLabels())

    # Relational labels.
    for client_id in self.client_ids[:2]:
      labels = data_store.REL_DB.GetClientLabels(client_id.Basename())
      self.assertEqual(len(labels), 2)
      self.assertEqual(labels[0].owner, self.token.username)
      self.assertEqual(labels[1].owner, self.token.username)
      self.assertItemsEqual([labels[0].name, labels[1].name], ["bar", "foo"])

    self.assertFalse(
        data_store.REL_DB.GetClientLabels(self.client_ids[2].Basename()))

  def _FindAuditEvent(self):
    for fd in audit.AllAuditLogs(token=self.token):
      for event in fd:
        if event.action == events.AuditEvent.Action.CLIENT_ADD_LABEL:
          for client_id in self.client_ids:
            if event.client == rdf_client.ClientURN(client_id):
              return event

  def testAuditEntryIsCreatedForEveryClient(self):
    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=self.client_ids, labels=["drei", "ein", "zwei"]),
        token=self.token)

    # We need to run .Simulate() so that the appropriate event is fired,
    # collected, and finally written to the logs that we inspect.
    mock_worker = worker_test_lib.MockWorker(token=self.token)
    mock_worker.Simulate()

    event = self._FindAuditEvent()
    self.assertIsNotNone(event)
    self.assertEqual(event.user, self.token.username)
    self.assertEqual(event.description, "%s.drei,%s.ein,%s.zwei" %
                     (self.token.username, self.token.username,
                      self.token.username))


class ApiRemoveClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiRemoveClientsLabelsHandler."""

  def setUp(self):
    super(ApiRemoveClientsLabelsHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiRemoveClientsLabelsHandler()

  def testRemovesUserLabelFromSingleClient(self):
    with aff4.FACTORY.Open(
        self.client_ids[0], mode="rw", token=self.token) as grr_client:
      grr_client.AddLabels(["foo", "bar"])
      data_store.REL_DB.WriteClientMetadata(
          self.client_ids[0].Basename(), fleetspeak_enabled=False)
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(),
                                        self.token.username, ["foo", "bar"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "bar")
    self.assertEqual(labels[0].owner, self.token.username)

    # Relational labels.
    labels = data_store.REL_DB.GetClientLabels(self.client_ids[0].Basename())
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "bar")
    self.assertEqual(labels[0].owner, self.token.username)

  def testDoesNotRemoveSystemLabelFromSingleClient(self):
    idx = client_index.ClientIndex()
    with aff4.FACTORY.Open(
        self.client_ids[0], mode="rw", token=self.token) as grr_client:
      grr_client.AddLabel("foo", owner="GRR")
      data_store.REL_DB.WriteClientMetadata(
          self.client_ids[0].Basename(), fleetspeak_enabled=False)
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(), "GRR",
                                        ["foo"])
      idx.AddClientLabels(self.client_ids[0].Basename(), ["foo"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)

    # Relational labels.
    labels = data_store.REL_DB.GetClientLabels(self.client_ids[0].Basename())
    self.assertEqual(len(labels), 1)
    # The label is still in the index.
    self.assertEqual(
        idx.LookupClients(["label:foo"]), [self.client_ids[0].Basename()])

  def testRemovesUserLabelWhenSystemLabelWithSimilarNameAlsoExists(self):
    idx = client_index.ClientIndex()
    with aff4.FACTORY.Open(
        self.client_ids[0], mode="rw", token=self.token) as grr_client:
      grr_client.AddLabel("foo")
      grr_client.AddLabel("foo", owner="GRR")
      data_store.REL_DB.WriteClientMetadata(
          self.client_ids[0].Basename(), fleetspeak_enabled=False)
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(),
                                        self.token.username, ["foo"])
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(), "GRR",
                                        ["foo"])
      idx.AddClientLabels(self.client_ids[0].Basename(), ["foo"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, "GRR")

    # Relational labels.
    labels = data_store.REL_DB.GetClientLabels(self.client_ids[0].Basename())
    self.assertEqual(len(labels), 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, "GRR")
    # The label is still in the index.
    self.assertEqual(
        idx.LookupClients(["label:foo"]), [self.client_ids[0].Basename()])


class ApiLabelsRestrictedSearchClientsHandlerTest(
    api_test_lib.ApiCallHandlerTest):
  """Test for ApiLabelsRestrictedSearchClientsHandler."""

  def setUp(self):
    super(ApiLabelsRestrictedSearchClientsHandlerTest, self).setUp()

    self.client_ids = self.SetupClients(4)

    index = client_index.CreateClientIndex(token=self.token)

    def LabelClient(i, label, owner):
      with aff4.FACTORY.Open(
          self.client_ids[i], mode="rw", token=self.token) as grr_client:
        grr_client.AddLabel(label, owner=owner)
        index.AddClient(grr_client)

    LabelClient(0, "foo", "david")
    LabelClient(1, "not-foo", "david")
    LabelClient(2, "bar", "peter_another")
    LabelClient(3, "bar", "peter")

    self.handler = client_plugin.ApiLabelsRestrictedSearchClientsHandler(
        labels_whitelist=["foo", "bar"],
        labels_owners_whitelist=["david", "peter"])

  def testSearchWithoutArgsReturnsOnlyClientsWithWhitelistedLabels(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(), token=self.token)

    self.assertEqual(len(result.items), 2)
    sorted_items = sorted(result.items, key=lambda r: r.client_id)

    self.assertEqual(sorted_items[0].client_id, self.client_ids[0])
    self.assertEqual(sorted_items[1].client_id, self.client_ids[3])

  def testSearchWithNonWhitelistedLabelReturnsNothing(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:not-foo"),
        token=self.token)
    self.assertFalse(result.items)

  def testSearchWithWhitelistedLabelReturnsSubSet(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:foo"), token=self.token)
    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:bar"), token=self.token)
    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithWhitelistedClientIdsReturnsSubSet(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[0].Basename()),
        token=self.token)
    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[3].Basename()),
        token=self.token)
    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithBlacklistedClientIdsReturnsNothing(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[1].Basename()),
        token=self.token)
    self.assertFalse(result.items)

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[2].Basename()),
        token=self.token)
    self.assertFalse(result.items)


class ApiInterrogateClientHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiInterrogateClientHandler."""

  def setUp(self):
    super(ApiInterrogateClientHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = client_plugin.ApiInterrogateClientHandler()

  def testInterrogateFlowIsStarted(self):
    flows_fd = aff4.FACTORY.Open(self.client_id.Add("flows"), token=self.token)
    flows_urns = list(flows_fd.ListChildren())
    self.assertEqual(len(flows_urns), 0)

    args = client_plugin.ApiInterrogateClientArgs(client_id=self.client_id)
    result = self.handler.Handle(args, token=self.token)

    flows_fd = aff4.FACTORY.Open(self.client_id.Add("flows"), token=self.token)
    flows_urns = list(flows_fd.ListChildren())
    self.assertEqual(len(flows_urns), 1)
    self.assertEqual(str(flows_urns[0]), result.operation_id)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
