#!/usr/bin/env python
"""Tests for API client and labels-related API calls."""

from absl import app

from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib


class ApiClientLibLabelsTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testAddLabelsRaisesOnIncorrectArgs(self):
    client_ref = self.api.Client(client_id=self.client_id)
    with self.assertRaises(ValueError):
      client_ref.AddLabels([])

    with self.assertRaises(TypeError):
      client_ref.AddLabels("string")

    with self.assertRaises(TypeError):
      client_ref.AddLabels([42])

  def testAddLabels(self):
    with test_lib.FakeTime(42):
      client_ref = self.api.Client(client_id=self.client_id)
      self.assertEqual(list(client_ref.Get().data.labels), [])
      client_ref.AddLabels(["foo", "bar"])

    self.assertCountEqual(
        client_ref.Get().data.labels,
        [
            objects_pb2.ClientLabel(name="bar", owner=self.test_username),
            objects_pb2.ClientLabel(name="foo", owner=self.test_username),
        ],
    )

  def testAddLabelsWithGeneratorArg(self):
    with test_lib.FakeTime(42):
      client_ref = self.api.Client(client_id=self.client_id)
      self.assertEqual(list(client_ref.Get().data.labels), [])

      def Gen():
        yield "foo"
        yield "bar"

      client_ref.AddLabels(Gen())

    self.assertCountEqual(
        client_ref.Get().data.labels,
        [
            objects_pb2.ClientLabel(name="bar", owner=self.test_username),
            objects_pb2.ClientLabel(name="foo", owner=self.test_username),
        ],
    )

  def testRemoveLabelsRaisesOnIncorrectArgs(self):
    client_ref = self.api.Client(client_id=self.client_id)
    with self.assertRaises(ValueError):
      client_ref.RemoveLabels([])

    with self.assertRaises(TypeError):
      client_ref.RemoveLabels("string")

    with self.assertRaises(TypeError):
      client_ref.RemoveLabels([42])

  def testRemoveLabel(self):
    with test_lib.FakeTime(42):
      data_store.REL_DB.AddClientLabels(
          self.client_id, self.test_username, ["bar", "foo"]
      )

    client_ref = self.api.Client(client_id=self.client_id)
    self.assertCountEqual(
        client_ref.Get().data.labels,
        [
            objects_pb2.ClientLabel(name="bar", owner=self.test_username),
            objects_pb2.ClientLabel(name="foo", owner=self.test_username),
        ],
    )

    client_ref.RemoveLabel("foo")
    self.assertCountEqual(
        client_ref.Get().data.labels,
        [objects_pb2.ClientLabel(name="bar", owner=self.test_username)],
    )

  def testRemoveLabelsWithGeneratorArg(self):
    with test_lib.FakeTime(42):
      data_store.REL_DB.AddClientLabels(
          self.client_id, self.test_username, ["bar", "foo"]
      )

    client_ref = self.api.Client(client_id=self.client_id)

    def Gen():
      yield "foo"
      yield "bar"

    client_ref.RemoveLabels(Gen())

    self.assertEmpty(client_ref.Get().data.labels)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
